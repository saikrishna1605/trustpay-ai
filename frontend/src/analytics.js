export const LEVELS = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'];
export const COLORS = {LOW:'#20a889', MEDIUM:'#e6ad45', HIGH:'#e87d55', CRITICAL:'#d95170'};
export function metrics(rows){
 const total=rows.length;
 return {total,high:rows.filter(r=>['HIGH','CRITICAL'].includes(r.risk_level)).length,
 completed:rows.filter(r=>r.payment_status==='COMPLETED').length,
 ai:rows.filter(r=>r.ai_status==='ok').length,
 average:total?Math.round(rows.reduce((s,r)=>s+r.risk_score,0)/total):0};
}
export function dailyCounts(rows,now=new Date()){
 const days=Array.from({length:7},(_,i)=>{const date=new Date(Date.UTC(now.getUTCFullYear(),now.getUTCMonth(),now.getUTCDate()-6+i));return {date:date.toISOString().slice(0,10),count:0};});
 for(const r of rows){const date=new Date(r.created_at);if(Number.isNaN(date.valueOf()))continue;const day=days.find(d=>d.date===date.toISOString().slice(0,10));if(day)day.count++;}
 return days;
}
export function distribution(rows){return LEVELS.map(level=>({level,count:rows.filter(r=>r.risk_level===level).length}));}
export function currencyTotals(rows){const totals={};for(const r of rows.filter(r=>r.payment_status==='COMPLETED'))totals[r.currency]=(totals[r.currency]||0)+r.amount;return totals;}
