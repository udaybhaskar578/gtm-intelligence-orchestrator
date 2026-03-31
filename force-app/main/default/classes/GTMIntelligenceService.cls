public with sharing class GTMIntelligenceService {

    public static Map<String, Object> enrichAccount(
        String accountId,
        String companyName,
        String industry,
        String domain
    ) {
        HttpRequest req = new HttpRequest();
        req.setEndpoint('callout:GTM_Backend/v1/analyze-account');
        req.setMethod('POST');
        req.setTimeout(120000);
        req.setHeader('Content-Type', 'application/json');

        Map<String, Object> body = new Map<String, Object>{
            'account_id'           => accountId,
            'company_name'         => companyName,
            'industry'             => industry,
            'domain'               => domain,
            'write_to_salesforce'  => false,
            'include_raw_intelligence' => false
        };
        req.setBody(JSON.serialize(body));

        Http http = new Http();
        HttpResponse res = http.send(req);

        if (res.getStatusCode() >= 400) {
            throw new GTMCalloutException(
                'Backend returned HTTP ' + res.getStatusCode() + ': ' + res.getBody().abbreviate(500)
            );
        }

        Map<String, Object> parsed = (Map<String, Object>) JSON.deserializeUntyped(res.getBody());
        return parsed;
    }

    public class GTMCalloutException extends Exception {}
}
