@IsTest
private class GTMIntelligenceServiceTest {
    private class SuccessMock implements HttpCalloutMock {
        public HttpResponse respond(HttpRequest req) {
            System.assertEquals('POST', req.getMethod());
            System.assertEquals('callout:GTM_Backend/v1/analyze-account', req.getEndpoint());
            System.assertEquals('application/json', req.getHeader('Content-Type'));

            Map<String, Object> body = (Map<String, Object>) JSON.deserializeUntyped(req.getBody());
            System.assertEquals('001000000000001AAA', (String) body.get('account_id'));
            System.assertEquals('Acme Corp', (String) body.get('company_name'));
            System.assertEquals('Software', (String) body.get('industry'));
            System.assertEquals('acme.com', (String) body.get('domain'));
            System.assertEquals(false, (Boolean) body.get('write_to_salesforce'));
            System.assertEquals(false, (Boolean) body.get('include_raw_intelligence'));

            HttpResponse res = new HttpResponse();
            res.setStatusCode(200);
            res.setBody('{"run_id":"run-123","battle_card":{"company_overview":"Overview"}}');
            return res;
        }
    }

    private class ErrorMock implements HttpCalloutMock {
        public HttpResponse respond(HttpRequest req) {
            HttpResponse res = new HttpResponse();
            res.setStatusCode(500);
            res.setBody('{"detail":"backend down"}');
            return res;
        }
    }

    @IsTest
    static void enrichAccount_returnsParsedResponseOnSuccess() {
        Test.setMock(HttpCalloutMock.class, new SuccessMock());

        Test.startTest();
        Map<String, Object> result = GTMIntelligenceService.enrichAccount(
            '001000000000001AAA',
            'Acme Corp',
            'Software',
            'acme.com'
        );
        Test.stopTest();

        System.assertEquals('run-123', (String) result.get('run_id'));
        System.assertNotEquals(null, result.get('battle_card'));
    }

    @IsTest
    static void enrichAccount_throwsOnHttpError() {
        Test.setMock(HttpCalloutMock.class, new ErrorMock());

        Test.startTest();
        try {
            GTMIntelligenceService.enrichAccount(
                '001000000000001AAA',
                'Acme Corp',
                'Software',
                'acme.com'
            );
            System.assert(false, 'Expected GTMCalloutException to be thrown');
        } catch (GTMIntelligenceService.GTMCalloutException ex) {
            System.assert(ex.getMessage().contains('Backend returned HTTP 500'));
        }
        Test.stopTest();
    }
}
