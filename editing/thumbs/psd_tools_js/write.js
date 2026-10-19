const fs=require('fs'); const ag=require('ag-psd'); const path=require('path');
const [dir,out,comp]=process.argv.slice(2);
const L=JSON.parse(fs.readFileSync(path.join(dir,'layers.json')));
const bm={NORMAL:'normal',OVERLAY:'overlay',MULTIPLY:'multiply'};
const children=L.map(l=>({name:l.name,left:l.left,top:l.top,right:l.left+l.w,bottom:l.top+l.h,
  blendMode:bm[l.blend]||'normal',opacity:l.opacity/255,
  imageData:{width:l.w,height:l.h,data:new Uint8ClampedArray(fs.readFileSync(path.join(dir,'..',l.file)))}}));
const c=fs.readFileSync(comp); // 1280x720 RGBA raw
const psd={width:1280,height:720,children,imageData:{width:1280,height:720,data:new Uint8ClampedArray(c)}};
fs.writeFileSync(out, Buffer.from(ag.writePsd(psd,{generateThumbnail:false})));
console.log('wrote',out);
