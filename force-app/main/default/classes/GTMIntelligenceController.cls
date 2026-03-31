public with sharing class GTMIntelligenceController {

    @AuraEnabled
    public static Map<String, Object> triggerEnrichment(Id accountId) {
        Account acct = [
            SELECT Name, Industry, Website
            FROM Account
            WHERE Id = :accountId
            WITH USER_MODE
            LIMIT 1
        ];

        String domain = null;
        if (String.isNotBlank(acct.Website)) {
            domain = acct.Website.replaceAll('https?://(www\\.)?', '').split('/')[0];
        }

        Map<String, Object> response = GTMIntelligenceService.enrichAccount(
            accountId,
            acct.Name,
            acct.Industry,
            domain
        );

        Map<String, Object> battleCard = (Map<String, Object>) response.get('battle_card');
        if (battleCard == null) {
            throw new AuraHandledException('Invalid response from backend: missing battle_card');
        }

        List<Object> topContactsRaw = (List<Object>) response.get('top_contacts');

        Account update_acct = new Account(Id = accountId);
        update_acct.GTM_Company_Overview__c      = (String) battleCard.get('company_overview');
        update_acct.GTM_Competitive_Positioning__c = (String) battleCard.get('competitive_positioning');
        update_acct.GTM_Recommended_Approach__c  = (String) battleCard.get('recommended_approach');
        update_acct.GTM_Confidence_Score__c      = toDecimal(battleCard.get('confidence_score'));
        update_acct.GTM_Last_Enriched__c         = DateTime.now();
        update_acct.GTM_Run_ID__c                = (String) response.get('run_id');

        List<Object> talkingPoints = (List<Object>) battleCard.get('talking_points');
        if (talkingPoints != null) {
            update_acct.GTM_Talking_Points__c = joinList(talkingPoints);
        }

        List<Object> risks = (List<Object>) battleCard.get('risks_and_objections');
        if (risks != null) {
            update_acct.GTM_Risks_Objections__c = joinList(risks);
        }

        List<Object> nextSteps = (List<Object>) battleCard.get('next_steps');
        if (nextSteps != null) {
            update_acct.GTM_Next_Steps__c = joinList(nextSteps);
        }

        if (topContactsRaw != null) {
            update_acct.GTM_Contacts_JSON__c = JSON.serialize(topContactsRaw);
        }

        update update_acct;

        return new Map<String, Object>{
            'success'  => true,
            'run_id'   => response.get('run_id'),
            'enriched_at' => String.valueOf(DateTime.now())
        };
    }

    @AuraEnabled(cacheable=true)
    public static Account getBattleCardData(Id accountId) {
        return [
            SELECT Name,
                   GTM_Last_Enriched__c,
                   GTM_Company_Overview__c,
                   GTM_Competitive_Positioning__c,
                   GTM_Recommended_Approach__c,
                   GTM_Talking_Points__c,
                   GTM_Risks_Objections__c,
                   GTM_Next_Steps__c,
                   GTM_Confidence_Score__c,
                   GTM_Run_ID__c,
                   GTM_Contacts_JSON__c
            FROM Account
            WHERE Id = :accountId
            WITH USER_MODE
            LIMIT 1
        ];
    }

    @AuraEnabled
    public static List<Id> createContacts(Id accountId, String contactsJson) {
        List<Object> raw = (List<Object>) JSON.deserializeUntyped(contactsJson);
        List<Contact> toInsert = new List<Contact>();

        for (Object item : raw) {
            Map<String, Object> c = (Map<String, Object>) item;
            Contact con = new Contact();
            con.AccountId  = accountId;
            con.LastName   = extractLastName((String) c.get('name'));
            con.FirstName  = extractFirstName((String) c.get('name'));
            con.Email      = (String) c.get('email');
            con.Title      = (String) c.get('title');
            con.Phone      = (String) c.get('phone');
            toInsert.add(con);
        }

        insert toInsert;

        List<Id> createdIds = new List<Id>();
        for (Contact con : toInsert) {
            createdIds.add(con.Id);
        }
        return createdIds;
    }

    private static String joinList(List<Object> items) {
        List<String> parts = new List<String>();
        for (Object item : items) {
            parts.add((String) item);
        }
        return String.join(parts, '\n• ');
    }

    private static Decimal toDecimal(Object val) {
        if (val == null) return null;
        if (val instanceof Decimal) return (Decimal) val;
        if (val instanceof Integer) return Decimal.valueOf((Integer) val);
        return Decimal.valueOf(String.valueOf(val));
    }

    private static String extractFirstName(String fullName) {
        if (String.isBlank(fullName)) return '';
        List<String> parts = fullName.trim().split('\\s+');
        return parts.size() > 1 ? parts[0] : '';
    }

    private static String extractLastName(String fullName) {
        if (String.isBlank(fullName)) return fullName;
        Integer spaceIdx = fullName.trim().indexOf(' ');
        return spaceIdx > -1 ? fullName.trim().substring(spaceIdx + 1).trim() : fullName.trim();
    }
}
