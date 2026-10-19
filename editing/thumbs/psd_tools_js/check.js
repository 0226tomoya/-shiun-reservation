const fs=require('fs'); const ag=require('ag-psd');
const mk=(w,h)=>({width:w,height:h,getContext:()=>({createImageData:(w,h)=>({width:w,height:h,data:new Uint8ClampedArray(w*h*4)}),putImageData(){},drawImage(){},getImageData:(x,y,w,h)=>({width:w,height:h,data:new Uint8ClampedArray(w*h*4)})})});
ag.initializeCanvas(mk,(d)=>mk(1,1));
for (const f of process.argv.slice(2)) {
  try { const p=ag.readPsd(fs.readFileSync(f),{useImageData:true,skipThumbnail:true});
    const walk=(ls)=>{let n=0;for(const l of ls||[]){n++;n+=walk(l.children)}return n};
    const so=[];const w2=(ls)=>{for(const l of ls||[]){if(l.placedLayer)so.push(l.name);w2(l.children)}};w2(p.children);
    console.log('OK',f.split('/').pop(),p.width,p.height,'layers',walk(p.children),'linked',(p.linkedFiles||[]).map(x=>x.name+':'+(x.data?x.data.length:0)),'so',so);
  } catch(e){ console.log('NG',f.split('/').pop(),e.message.slice(0,300)); }
}
