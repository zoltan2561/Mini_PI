"use strict";
document.querySelectorAll("form[data-confirm]").forEach(form=>form.addEventListener("submit",event=>{if(!confirm(form.dataset.confirm))event.preventDefault();}));
document.querySelectorAll("[data-copy]").forEach(button=>button.addEventListener("click",async()=>{
  const field=document.getElementById(button.dataset.copy);field.select();
  try{if(navigator.clipboard?.writeText)await navigator.clipboard.writeText(field.value);else if(!document.execCommand("copy"))throw new Error();button.textContent="Kimásolva ✓";}catch(_){button.textContent="A kijelölt kulcsot másold ki kézzel";}
}));
function sizePreview(){document.querySelectorAll(".preview-viewport").forEach(view=>{const scale=view.clientWidth/480;view.style.height=(320*scale)+"px";view.querySelector("iframe").style.transform=`scale(${scale})`;});}
sizePreview();addEventListener("resize",sizePreview);
