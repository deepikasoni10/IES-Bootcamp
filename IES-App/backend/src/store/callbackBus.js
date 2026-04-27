/**
 * In-process event bus for mock Beckn callbacks.
 * Routes on_init / on_confirm / on_status events to the correct filing.
 * In real ONIX mode, callbacks arrive via HTTP POST /callback/on_*
 */
import { EventEmitter } from 'events';
export const callbackBus = new EventEmitter();
callbackBus.setMaxListeners(100);
