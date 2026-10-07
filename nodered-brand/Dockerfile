# CHERT IoT — branded Node-RED: Arabic (ar-AR) as a first-class, LTR-only editor language.
#
# Standard image-layer brand (mirrors thingsboard-brand/): FROM the pinned upstream image, add the
# committed ar-AR catalogs to the canonical editor-client locales dir, register the label in every
# locale's `languages` map, and set the default editor language to Arabic. All at BUILD time, baked
# into an immutable artifact — no runtime copy/mount/init, no RTL. See docs/ar-AR/ for the plan +
# the master prompt, and docs/audit/ for the evidence report.
ARG NODERED_VERSION=5.0.6
FROM ghcr.io/chertsa/chertiot-base-node-red:${NODERED_VERSION}

USER root
ARG EC=/usr/src/node-red/node_modules/@node-red/editor-client
ARG LOC=${EC}/locales
ARG PUB=${EC}/public/red

# 1) Committed Arabic catalogs → canonical locales path (served verbatim by the runtime i18n dir-scan).
COPY --chown=node-red:node-red locales/ar-AR/ ${LOC}/ar-AR/

# 2) Register "ar-AR": "العربية" in every locale's editor.json languages map (so Arabic is offered in
#    the selector whatever the active UI language) and 3) default the editor language to Arabic by
#    patching detectLanguage() in the built client. Every mutation is count-asserted: a zero-hit
#    replace FAILS the build rather than shipping a silent no-op (frozen pin ⇒ anchors are stable).
RUN node -e ' \
  const fs=require("fs"),path=require("path"); \
  const loc=process.env.LOC||"'"${LOC}"'"; \
  let touched=0; \
  for(const d of fs.readdirSync(loc)){ \
    const p=path.join(loc,d,"editor.json"); \
    if(!fs.existsSync(p))continue; \
    const j=JSON.parse(fs.readFileSync(p,"utf8")); \
    j.languages=j.languages||{}; \
    if(j.languages["ar-AR"]!=="العربية"){j.languages["ar-AR"]="العربية";fs.writeFileSync(p,JSON.stringify(j,null,4)+"\n");touched++;} \
  } \
  console.log("languages.ar-AR written to",touched,"catalog(s)"); \
  if(touched<2){throw new Error("expected ar-AR label in en-US + ar-AR at least; got "+touched);} \
' \
 && node -e ' \
  const fs=require("fs"); \
  const pub=process.env.PUB||"'"${PUB}"'"; \
  for(const [f,needle] of [["red.min.js","){return navigator.language}"],["red.js","return navigator.language"]]){ \
    const fp=pub+"/"+f; \
    if(!fs.existsSync(fp)) throw new Error("missing "+fp); \
    const src=fs.readFileSync(fp,"utf8"); \
    const n=src.split(needle).length-1; \
    if(n!==1) throw new Error(f+": expected exactly 1 detectLanguage anchor, found "+n); \
    const repl = f==="red.min.js" ? "){return\"ar-AR\"}" : "return \"ar-AR\""; \
    fs.writeFileSync(fp, src.replace(needle,repl)); \
    console.log(f+": default editor language set to ar-AR"); \
  } \
'

USER node-red
