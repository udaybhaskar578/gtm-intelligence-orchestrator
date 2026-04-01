@IsTest
private class GTMIntelligenceControllerTest {
    private class EnrichmentSuccessMock implements HttpCalloutMock {
        public HttpResponse respond(HttpRequest req) {
            HttpResponse res = new HttpResponse();
            res.setStatusCode(200);
            res.setBody(
                '{"run_id":"run-456","battle_card":{' +
                    '"company_overview":"Acme overview",' +
                    '"competitive_positioning":"Acme positioning",' +
                    '"recommended_approach":"Acme approach",' +
                    '"confidence_score":88.5,' +
                    '"talking_points":["Point A","Point B"],' +
                    '"risks_and_objections":["Risk A","Risk B"],' +
                    '"next_steps":["Step A","Step B"]' +
                '},' +
                '"top_contacts":[{"name":"Jane Doe","email":"jane@acme.com","title":"VP Sales","phone":"123-456"}]' +
                '}'
            );
            return res;
        }
    }

    private class MissingBattleCardMock implements HttpCalloutMock {
        public HttpResponse respond(HttpRequest req) {
            HttpResponse res = new HttpResponse();
            res.setStatusCode(200);
            res.setBody('{"run_id":"run-789","top_contacts":[]}');
            return res;
        }
    }

    @IsTest
    static void triggerEnrichment_updatesAccountFieldsAndReturnsSuccess() {
        Account acct = new Account(Name = 'Acme Corp', Industry = 'Software', Website = 'https://www.acme.com');
        insert acct;

        Test.setMock(HttpCalloutMock.class, new EnrichmentSuccessMock());

        Test.startTest();
        Map<String, Object> result = GTMIntelligenceController.triggerEnrichment(acct.Id);
        Test.stopTest();

        System.assertEquals(true, (Boolean) result.get('success'));
        System.assertEquals('run-456', (String) result.get('run_id'));

        Account updated = [
            SELECT GTM_Company_Overview__c,
                   GTM_Competitive_Positioning__c,
                   GTM_Recommended_Approach__c,
                   GTM_Confidence_Score__c,
                   GTM_Talking_Points__c,
                   GTM_Risks_Objections__c,
                   GTM_Next_Steps__c,
                   GTM_Run_ID__c,
                   GTM_Last_Enriched__c,
                   GTM_Contacts_JSON__c
            FROM Account
            WHERE Id = :acct.Id
            LIMIT 1
        ];

        System.assertEquals('Acme overview', updated.GTM_Company_Overview__c);
        System.assertEquals('Acme positioning', updated.GTM_Competitive_Positioning__c);
        System.assertEquals('Acme approach', updated.GTM_Recommended_Approach__c);
        System.assertEquals(88.5, updated.GTM_Confidence_Score__c);
        System.assertEquals('Point A\n• Point B', updated.GTM_Talking_Points__c);
        System.assertEquals('Risk A\n• Risk B', updated.GTM_Risks_Objections__c);
        System.assertEquals('Step A\n• Step B', updated.GTM_Next_Steps__c);
        System.assertEquals('run-456', updated.GTM_Run_ID__c);
        System.assertNotEquals(null, updated.GTM_Last_Enriched__c);
        System.assert(updated.GTM_Contacts_JSON__c.contains('Jane Doe'));
    }

    @IsTest
    static void triggerEnrichment_throwsWhenBattleCardMissing() {
        Account acct = new Account(Name = 'Missing Card Co');
        insert acct;

        Test.setMock(HttpCalloutMock.class, new MissingBattleCardMock());

        Boolean threwExpected = false;
        Test.startTest();
        try {
            GTMIntelligenceController.triggerEnrichment(acct.Id);
            System.assert(false, 'Expected AuraHandledException');
        } catch (AuraHandledException ex) {
            threwExpected = true;
        }
        Test.stopTest();
        System.assertEquals(true, threwExpected, 'Expected AuraHandledException to be thrown');
    }

    @IsTest
    static void getBattleCardData_returnsAccountRecord() {
        Account acct = new Account(
            Name = 'Query Co',
            GTM_Company_Overview__c = 'Overview text',
            GTM_Run_ID__c = 'run-query'
        );
        insert acct;

        Account fetched = GTMIntelligenceController.getBattleCardData(acct.Id);
        System.assertEquals(acct.Id, fetched.Id);
        System.assertEquals('Query Co', fetched.Name);
        System.assertEquals('Overview text', fetched.GTM_Company_Overview__c);
        System.assertEquals('run-query', fetched.GTM_Run_ID__c);
    }

    @IsTest
    static void createContacts_insertsContactsAndReturnsIds() {
        Account acct = new Account(Name = 'Contacts Co');
        insert acct;

        String contactsJson = JSON.serialize(new List<Object>{
            new Map<String, Object>{
                'name' => 'Jane Smith',
                'email' => 'jane@contactsco.com',
                'title' => 'Director',
                'phone' => '111-222'
            },
            new Map<String, Object>{
                'name' => 'Madonna',
                'email' => 'madonna@contactsco.com',
                'title' => 'Advisor',
                'phone' => '333-444'
            }
        });

        Test.startTest();
        List<Id> ids = GTMIntelligenceController.createContacts(acct.Id, contactsJson);
        Test.stopTest();

        System.assertEquals(2, ids.size());

        List<Contact> created = [
            SELECT FirstName, LastName, Email, Title, Phone, AccountId
            FROM Contact
            WHERE Id IN :ids
            ORDER BY Email
        ];
        System.assertEquals(2, created.size());

        Contact jane = created[0];
        Contact madonna = created[1];

        System.assertEquals(acct.Id, jane.AccountId);
        System.assertEquals('Jane', jane.FirstName);
        System.assertEquals('Smith', jane.LastName);

        System.assertEquals(null, madonna.FirstName);
        System.assertEquals('Madonna', madonna.LastName);
    }
}
