import React, {useMemo, useState} from 'react';
import StudioView from './StudioView';
import {studioTheme} from 'ag-studio';
import {AgStudio, AgStudioProvider} from 'ag-studio-react';
const initialState={pages:[{id:'overview',widgets:{
 payments:{type:'grid',dataMapping:{cols:['product','seller','amount','currency','risk_score','risk_level','payment_status','checkout_locale'].map(k=>({id:`assessments.${k}`}))},format:{title:{enabled:true,text:'Purchase risk & payment activity'}}},
 risk:{type:'bar-chart-grouped',dataMapping:{categoryKey:[{id:'assessments.risk_level'}],valueKey:[{id:'assessments.risk_score',aggregation:'avg'}]},format:{title:{enabled:true,text:'Average risk score by level'}}}
},widgetLayout:{payments:{xTrack:0,yTrack:0,xSpan:24,ySpan:22},risk:{xTrack:0,yTrack:22,xSpan:24,ySpan:14}}}],selectedPageId:'overview'};
export default function Studio({rows,appearance='light'}){
 const [mode,setMode]=useState('view');
 const reportTheme=useMemo(()=>studioTheme.withParams({studioWidgetTitleFontSize:16,studioWidgetTitleFontWeight:600,studioWidgetPadding:18,studioWidgetBorderRadius:12,gridRowHeight:48,gridFontSize:12,chartFontSize:12,...(appearance==='dark'?{
  backgroundColor:'#17243a',foregroundColor:'#dce5f5',textColor:'#dce5f5',borderColor:'#2c3e58',browserColorScheme:'dark',gridBrowserColorScheme:'dark',gridCellTextColor:'#dce5f5',gridHeaderTextColor:'#dce5f5',
  studioCanvasBackgroundColor:'#101b2d',studioWidgetBackgroundColor:'#17243a',
  studioWidgetTitleTextColor:'#e1e9f8',studioWidgetSubtitleTextColor:'#a0b2cd',
  gridDataBackgroundColor:'#17243a',gridOddRowBackgroundColor:'#1b2a42',gridHeaderBackgroundColor:'#1e2f49',
  chartBackgroundColor:'#17243a',fontFamily:'Inter, -apple-system, sans-serif'
 }:{backgroundColor:'#ffffff',foregroundColor:'#25334d',textColor:'#25334d',browserColorScheme:'light',borderColor:'#e3e9f3',studioCanvasBackgroundColor:'#f6f8fc',studioWidgetTitleTextColor:'#25334d',fontFamily:'Inter, -apple-system, sans-serif'})}),[appearance]);
 const data=useMemo(()=>({sources:[{id:'assessments',data:rows.map(row=>({...row,checkout_locale:row.checkout_locale||'Not created'}))}]}),[rows]);
 if(!rows.length)return <div className="empty"><h3>No report data yet</h3><p>Run a purchase review first. AG Studio will load your stored assessments here.</p></div>;
 return <div className="studio-wrapper"><div className="studio-toolbar"><span>Purchase intelligence report</span><div><button className={mode==='view'?'active':''} onClick={()=>setMode('view')}>View report</button><button className={mode==='edit'?'active':''} onClick={()=>setMode('edit')}>Edit report</button></div></div><div className={`studio-canvas ${mode==='view'?'custom-report-canvas':''}`}>{mode==='view'?<StudioView rows={rows}/>:<AgStudioProvider licenseKey={import.meta.env.VITE_AG_STUDIO_LICENSE_KEY||undefined}><AgStudio theme={reportTheme} style={{height:'100%',width:'100%'}} data={data} initialState={initialState} mode={mode} panels={{edit:{right:['edit','data']}}}/></AgStudioProvider>}</div></div>;
}
