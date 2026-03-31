import { LightningElement, api, wire } from 'lwc';
import { CloseActionScreenEvent } from 'lightning/actions';
import { getRecord, getFieldValue } from 'lightning/uiRecordApi';
import NAME_FIELD from '@salesforce/schema/Account.Name';
import triggerEnrichment from '@salesforce/apex/GTMIntelligenceController.triggerEnrichment';

const FIELDS = [NAME_FIELD];

const STATE = { LOADING: 'loading', SUCCESS: 'success', ERROR: 'error' };

export default class GtmEnrichAction extends LightningElement {
    @api recordId;

    state = STATE.LOADING;
    errorMessage = null;

    @wire(getRecord, { recordId: '$recordId', fields: FIELDS })
    wiredRecord({ data }) {
        if (data) {
            this._accountName = getFieldValue(data, NAME_FIELD);
            this._runEnrichment();
        }
    }

    get accountName() {
        return this._accountName || '';
    }

    get isLoading() { return this.state === STATE.LOADING; }
    get isSuccess() { return this.state === STATE.SUCCESS; }
    get isError()   { return this.state === STATE.ERROR; }

    async _runEnrichment() {
        this.state = STATE.LOADING;
        this.errorMessage = null;
        try {
            await triggerEnrichment({ accountId: this.recordId });
            this.state = STATE.SUCCESS;
        } catch (error) {
            this.state = STATE.ERROR;
            this.errorMessage = error.body?.message || error.message || 'Unknown error occurred.';
        }
    }

    handleRetry() {
        this._runEnrichment();
    }

    handleClose() {
        this.dispatchEvent(new CloseActionScreenEvent());
    }
}
