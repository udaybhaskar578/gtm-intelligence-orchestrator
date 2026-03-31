import { LightningElement, api, wire, track } from 'lwc';
import { ShowToastEvent } from 'lightning/platformShowToastEvent';
import { refreshApex } from '@salesforce/apex';
import getBattleCardData from '@salesforce/apex/GTMIntelligenceController.getBattleCardData';
import triggerEnrichment from '@salesforce/apex/GTMIntelligenceController.triggerEnrichment';
import createContacts from '@salesforce/apex/GTMIntelligenceController.createContacts';

export default class GtmBattleCard extends LightningElement {
    @api recordId;

    @track isEnriching = false;
    @track errorMessage = null;
    @track contacts = [];

    _wiredResult;
    battleCard = null;

    @wire(getBattleCardData, { accountId: '$recordId' })
    wiredBattleCard(result) {
        this._wiredResult = result;
        if (result.data) {
            this.battleCard = result.data;
            this._initContacts(result.data.GTM_Contacts_JSON__c);
            this.errorMessage = null;
        } else if (result.error) {
            this.errorMessage = result.error.body?.message || 'Failed to load battle card data.';
        }
    }

    get isNotEnriched() {
        return !this.isEnriching && !this.hasError && !this.battleCard?.GTM_Last_Enriched__c;
    }

    get isEnriched() {
        return !this.isEnriching && !this.hasError && !!this.battleCard?.GTM_Last_Enriched__c;
    }

    get hasError() {
        return !this.isEnriching && !!this.errorMessage;
    }

    get formattedLastEnriched() {
        if (!this.battleCard?.GTM_Last_Enriched__c) return '';
        return new Date(this.battleCard.GTM_Last_Enriched__c).toLocaleString();
    }

    get confidenceScore() {
        return this.battleCard?.GTM_Confidence_Score__c ?? '--';
    }

    get runId() {
        return this.battleCard?.GTM_Run_ID__c;
    }

    get talkingPoints() {
        return this._splitBulletField(this.battleCard?.GTM_Talking_Points__c);
    }

    get risks() {
        return this._splitBulletField(this.battleCard?.GTM_Risks_Objections__c);
    }

    get nextSteps() {
        return this._splitBulletField(this.battleCard?.GTM_Next_Steps__c);
    }

    get hasContacts() {
        return this.contacts && this.contacts.length > 0;
    }

    get noContactsSelected() {
        return !this.contacts.some(c => c.selected);
    }

    handleContactSelect(event) {
        const id = event.target.dataset.id;
        this.contacts = this.contacts.map(c =>
            c.id === id ? { ...c, selected: event.target.checked } : c
        );
    }

    async handleEnrich() {
        this.isEnriching = true;
        this.errorMessage = null;
        try {
            await triggerEnrichment({ accountId: this.recordId });
            await refreshApex(this._wiredResult);
            this.dispatchEvent(new ShowToastEvent({
                title: 'Battle card ready!',
                message: 'Account has been successfully enriched.',
                variant: 'success'
            }));
        } catch (error) {
            this.errorMessage = error.body?.message || error.message || 'Enrichment failed.';
            this.dispatchEvent(new ShowToastEvent({
                title: 'Enrichment failed',
                message: this.errorMessage,
                variant: 'error'
            }));
        } finally {
            this.isEnriching = false;
        }
    }

    async handleCreateContacts() {
        const selected = this.contacts.filter(c => c.selected);
        if (!selected.length) return;

        try {
            const createdIds = await createContacts({
                accountId: this.recordId,
                contactsJson: JSON.stringify(selected)
            });
            this.dispatchEvent(new ShowToastEvent({
                title: 'Contacts created',
                message: `${createdIds.length} contact(s) created successfully.`,
                variant: 'success'
            }));
            this.contacts = this.contacts.map(c => ({ ...c, selected: false }));
        } catch (error) {
            this.dispatchEvent(new ShowToastEvent({
                title: 'Failed to create contacts',
                message: error.body?.message || error.message || 'Unknown error.',
                variant: 'error'
            }));
        }
    }

    _initContacts(contactsJson) {
        if (!contactsJson) {
            this.contacts = [];
            return;
        }
        try {
            const parsed = JSON.parse(contactsJson);
            this.contacts = parsed.map(c => ({ ...c, selected: false }));
        } catch {
            this.contacts = [];
        }
    }

    _splitBulletField(value) {
        if (!value) return [];
        return value.split('\n• ').map(s => s.replace(/^• /, '').trim()).filter(Boolean);
    }
}
