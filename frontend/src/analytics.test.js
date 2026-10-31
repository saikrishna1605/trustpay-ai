import test from 'node:test';
import assert from 'node:assert/strict';
import {metrics,dailyCounts,currencyTotals,distribution} from './analytics.js';
const rows=[{created_at:'2026-10-30T23:59:00Z',risk_score:80,risk_level:'CRITICAL',payment_status:'COMPLETED',currency:'USD',amount:10,ai_status:'ok'},
{created_at:'2026-10-31T01:00:00+04:00',risk_score:20,risk_level:'LOW',payment_status:'REFUNDED',currency:'USD',amount:20,ai_status:'failed'},
{created_at:'2026-10-31T00:01:00Z',risk_score:50,risk_level:'MEDIUM',payment_status:'COMPLETED',currency:'EUR',amount:30,ai_status:'ok'}];
test('payment metrics separate currencies and exclude refunded captures',()=>{assert.deepEqual(currencyTotals(rows),{USD:10,EUR:30});assert.equal(metrics(rows).completed,2);assert.equal(metrics(rows).high,1);});
test('UTC day counts do not assign local offset timestamp to the wrong date',()=>{const days=dailyCounts(rows,new Date('2026-10-31T12:00:00Z'));assert.equal(days[5].count,2);assert.equal(days[6].count,1);assert.equal(days.reduce((s,d)=>s+d.count,0),3);});
test('empty dashboard reports no invented metrics',()=>{assert.equal(metrics([]).total,0);assert.equal(distribution([]).reduce((s,r)=>s+r.count,0),0);assert.deepEqual(currencyTotals([]),{});});
