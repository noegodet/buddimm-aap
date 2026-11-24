// Rendu à partir de window.DATA (généré par src/pipeline.py). Aucune dépendance.
const D = window.DATA;
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const dt = iso => new Date(iso + "T00:00");
const fr = iso => iso ? dt(iso).toLocaleDateString("fr-FR", { day: "numeric", month: "long", year: "numeric" }) : "?";
const frShort = iso => dt(iso).toLocaleDateString("fr-FR", { day: "2-digit", month: "2-digit", year: "2-digit" });
const pct = x => x.toLocaleString("fr-FR", { maximumFractionDigits: 1 }) + " %";
const short = url => { const m = url.match(/recueil-(84-\d{4}-\d+)/); return m ? "RAA " + m[1] : "PDF ARS " + ((url.match(/media\/(\d+)/) || [])[1] || ""); };
const src = (url, page) => `<a class="src" href="${esc(url)}#page=${page}" target="_blank" rel="noopener">${esc(short(url))} · p.&nbsp;${page}</a>`;
const F = (doc, k) => doc?.champs?.[k];
const V = (doc, k) => F(doc, k)?.valeur;
const CAT = { qualite_projet: "Qualité du projet", cout_financement: "Coût / financement", experience_porteur: "Expérience du porteur",
              partenariats: "Partenariats", delai_mise_en_oeuvre: "Délai de mise en œuvre", implantation_immobilier: "Implantation / immobilier" };
const TYPE = t => ({ "appartements de coordination thérapeutique": "ACT", "équipe mobile santé précarité": "EMSP" }[t] || t || "");

// ---------- statuts (icône + libellé, jamais la couleur seule)
const ST = {
  found: ["good", "✓", "trouvé"], cited: ["warn", "◐", "citée"], missing: ["crit", "×", "non trouvé"],
  ok: ["good", "✓", "respecté"], over: ["crit", "×", "dépassé"], na: ["warn", "?", "non vérifiable"],
};
const pill = (k, label) => { const [c, i, l] = ST[k]; return `<span class="st ${c}"><i>${i}</i>${esc(label || l)}</span>`; };
const docState = (fi, k) => fi[k] ? "found" : (k === "autorisation" && fi.autorisation_citee) ? "cited" : "missing";
const delai = fi => fi.controles.find(c => c.regle.includes("6 mois"));
const delaiState = fi => ({ ok: "ok", "dépassé": "over" }[delai(fi)?.statut] || "na");
const meter = c => `<div class="meter" title="Somme d'indices (n° AAP, lauréat = bénéficiaire, délai légal), pas une probabilité">
  <div class="track"><div class="fill" style="width:${c.score * 100}%"></div></div><span class="num">fiabilité ${c.score.toLocaleString("fr-FR", { minimumFractionDigits: 1 })} / 1 · ${c.niveau}</span></div>`;

// ---------- tooltip partagé
const tip = document.getElementById("tip");
document.addEventListener("mouseover", e => {
  const t = e.target.closest("[data-tip]"); if (!t) { tip.style.opacity = 0; return; }
  tip.innerHTML = t.dataset.tip; tip.style.opacity = 1;
});
document.addEventListener("mousemove", e => {
  const x = Math.min(e.clientX + 14, innerWidth - tip.offsetWidth - 8);
  tip.style.left = x + "px"; tip.style.top = (e.clientY + 16) + "px";
});

// ---------- synthèse
function kpis() {
  const complete = D.fiches.filter(f => f.avis && f.classement && f.autorisation).length;
  const docs = D.fiches.reduce((n, f) => n + ["avis", "classement", "autorisation"].filter(k => f[k]).length, 0);
  const tiles = [
    ["AAP suivis", D.fiches.length, `dont ${D.fiches.filter(f => f.bonus).length} repérés en passant`],
    ["Chaînes complètes", `${complete} / ${D.fiches.length}`, "avis + classement + autorisation"],
    ["Documents reliés", docs, "chacun avec URL et page"],
    ["PDF parcourus", D.sources.length, "sources primaires, en cache"],
  ];
  document.getElementById("kpis").innerHTML = tiles.map(([l, v, h]) =>
    `<div class="kpi"><div class="label">${l}</div><div class="value num">${v}</div><div class="hint">${h}</div></div>`).join("");
}

function summary() {
  const rows = D.fiches.map(f => `<tr class="link" onclick="location.hash='aap-${f.aap_id}'">
    <td><a href="#aap-${f.aap_id}"><b>${esc(f.aap_id)}</b></a>${f.bonus ? '<span class="tag">bonus</span>' : ""}
      <div class="small muted">${esc(TYPE(f.type))}${f.places ? " · " + f.places + " places" : ""} · ${esc(f.territoire || "?")}</div></td>
    <td>${pill(docState(f, "avis"))}</td><td>${pill(docState(f, "classement"))}</td><td>${pill(docState(f, "autorisation"))}</td>
    <td>${pill(delaiState(f))}</td><td>${meter(f.confiance)}</td></tr>`).join("");
  document.getElementById("summary").innerHTML = `<table><thead><tr><th>AAP</th><th>Avis</th><th>Classement</th>
    <th>Autorisation</th><th>Délai ≤ 6 mois</th><th>Fiabilité du lien</th></tr></thead><tbody>${rows}</tbody></table>`;
}

// ---------- frise chronologique (SVG dessiné à la largeur réelle)
function events(fi) {
  const ev = [], add = (doc, k, label, kind) => { const f = F(doc, k); if (f) ev.push({ d: f.valeur, label, kind, url: f.url, page: f.page }); };
  add(fi.avis, "date_publication", "Publication de l'avis", "avis");
  add(fi.avis, "date_limite_depot", "Date limite de dépôt", "avis");
  add(fi.classement, "date_commission", "Commission de sélection", "classement");
  if (V(fi.classement, "date_avis_classement") !== V(fi.classement, "date_commission"))
    add(fi.classement, "date_avis_classement", "Avis de classement", "classement");
  add(fi.autorisation, "date_autorisation", "Autorisation signée", "autorisation");
  const c = fi.autorisation_citee;
  if (!fi.autorisation && c) ev.push({ d: c.date, label: "Autorisation (citée)", kind: "cite", url: c.url, page: c.page });
  return ev.sort((a, b) => a.d.localeCompare(b.d));
}

function timeline(fi, width) {
  const ev = events(fi); if (!ev.length) return "";
  const ctl = delai(fi), borne = ctl?.borne;
  const t = ev.map(e => +dt(e.d)).concat(borne ? [+dt(borne)] : []);
  const t0 = Math.min(...t), t1 = Math.max(...t), span = Math.max(t1 - t0, 864e5 * 30);
  const padL = 70, padR = 70, W = Math.max(width, 320);
  const x = d => padL + (+dt(d) - t0) / span * (W - padL - padR);
  const lineH = 15, step = 38;

  // étiquettes : on choisit le premier étage libre (haut 1, bas 1, haut 2, bas 2) pour éviter les chevauchements
  const tiers = [-1, 1, -2, 2], right = {};
  const marks = ev.map(e => ({ ...e, x: x(e.d) }));
  if (borne) marks.push({ d: borne, label: "Borne légale +6 mois", kind: "borne", x: x(borne) });
  marks.sort((a, b) => a.x - b.x);
  for (const m of marks) {
    const w = Math.max(m.label.length, 10) * 6.4 + 8;
    m.anchor = m.x - w / 2 < 4 ? "start" : m.x + w / 2 > W - 4 ? "end" : "middle";
    const left = m.anchor === "start" ? m.x : m.anchor === "end" ? m.x - w : m.x - w / 2;
    m.tier = tiers.find(ti => (right[ti] ?? -1e9) < left) ?? 2;
    right[m.tier] = left + w;
  }
  // hauteur ajustée aux étages réellement utilisés ; ty = ligne de base du libellé (la date est 15 px dessous)
  const up = Math.max(0, ...marks.filter(m => m.tier < 0).map(m => -m.tier));
  const down = Math.max(0, ...marks.filter(m => m.tier > 0).map(m => m.tier));
  const Y = 14 + up * step;
  const ty = tier => tier < 0 ? Y - 30 - (-tier - 1) * step : Y + 26 + (tier - 1) * step;
  const H = Y + 12 + down * step;

  let s = `<svg width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" role="img" aria-label="Frise chronologique de l'AAP ${esc(fi.aap_id)}">`;
  // fenêtre légale (date limite -> +6 mois)
  const lim = V(fi.avis, "date_limite_depot");
  if (lim && borne) {
    const a = x(lim), b = x(borne);
    s += `<rect x="${a}" y="${Y - 7}" width="${b - a}" height="14" rx="3" fill="var(--good-bg)"
      data-tip="Délai légal de décision : 6 mois après la date limite de dépôt (CASF R313-7)"/>`;
  }
  s += `<line x1="${padL - 20}" x2="${W - padR + 20}" y1="${Y}" y2="${Y}" stroke="var(--axis)" stroke-width="2" stroke-linecap="round"/>`;
  for (const m of marks) {
    const up = m.tier < 0, yl = ty(m.tier);  // NB : masque volontairement le `up` (nombre d'étages) ci-dessus
    s += `<line x1="${m.x}" x2="${m.x}" y1="${up ? yl + lineH + 5 : Y + 8}" y2="${up ? Y - 8 : yl - 13}" stroke="var(--axis)" stroke-width="1"/>`;
    if (m.kind === "borne") {
      s += `<line x1="${m.x}" x2="${m.x}" y1="${Y - 12}" y2="${Y + 12}" stroke="var(--ink-2)" stroke-width="2" stroke-dasharray="3 3"/>`;
    } else {
      const auto = m.kind === "autorisation" || m.kind === "cite";
      const st = auto && ctl?.statut === "ok" ? "var(--good)" : auto && ctl?.statut === "dépassé" ? "var(--critical)" : "var(--ink-2)";
      const tipTxt = `<b>${esc(m.label)}</b><br>${fr(m.d)}<br>${esc(short(m.url))} · p. ${m.page}`;
      s += m.kind === "cite"
        ? `<circle cx="${m.x}" cy="${Y}" r="6" fill="var(--surface)" stroke="${st === "var(--ink-2)" ? "var(--warning)" : st}" stroke-width="2.5"/>`
        : `<circle cx="${m.x}" cy="${Y}" r="6" fill="${st}" stroke="var(--surface)" stroke-width="2"/>`;
      s += `<a href="${esc(m.url)}#page=${m.page}" target="_blank" rel="noopener"><circle cx="${m.x}" cy="${Y}" r="14" fill="transparent" data-tip="${esc(tipTxt)}" style="cursor:pointer"/></a>`;
    }
    s += `<text x="${m.x}" y="${yl}" text-anchor="${m.anchor}" font-size="12.5" fill="var(--ink)" font-weight="600">${esc(m.label)}</text>`;
    s += `<text x="${m.x}" y="${yl + lineH}" text-anchor="${m.anchor}" font-size="12" fill="var(--ink-2)" class="num">${frShort(m.d)}</text>`;
  }
  return s + "</svg>";
}

// ---------- blocs détaillés
function docs(fi) {
  const a = fi.avis, c = fi.classement, au = fi.autorisation, ci = fi.autorisation_citee, nt = fi.non_trouve;
  const miss = k => `<p>${pill("missing")}</p><ul class="small muted">${(nt[k] || []).map(n => `<li>${esc(n)}</li>`).join("")}</ul>`;
  const rk = V(c, "classement");
  const benef = V(au, "beneficiaire") || ci?.beneficiaire;
  return `<div class="docs">
    <div class="doc"><h4>Avis d'appel à projets</h4>${a ? `
      <p>Dépôt jusqu'au <b>${fr(V(a, "date_limite_depot"))}</b></p>
      <p class="small muted">Acte p. ${a.pages[0]}–${a.pages[1]} · ${src(a.url, a.pages[0])}</p>` : miss("avis")}</div>
    <div class="doc"><h4>Classement de la commission</h4>${c ? `
      <p class="small muted">${esc(V(c, "nb_projets_recus") || "?")} projets reçus · commission du ${fr(V(c, "date_commission"))}</p>
      ${rk ? `<ol>${rk.map(e => `<li value="${e.rang}"><b>${esc(e.nom)}</b> <span class="muted small">${esc(e.forme)}${e.ex_aequo ? " · ex æquo" : ""}</span></li>`).join("")}</ol>` : ""}
      <p class="small muted">${src(c.url, c.pages[0])}</p>` : miss("classement")}</div>
    <div class="doc"><h4>Autorisation</h4>${au ? `
      <p>Acte n° <b class="num">${esc(V(au, "numero_acte") || "?")}</b> du ${fr(V(au, "date_autorisation"))}</p>
      <p>${benef ? `<b>${esc(benef.nom)}</b> <span class="muted small">${esc(benef.forme)}</span>` : '<span class="muted">bénéficiaire non extrait</span>'}</p>
      ${V(au, "places_mentionnees") ? `<p class="small muted">Places citées : ${V(au, "places_mentionnees").join(" ; ")}</p>` : ""}
      <p class="small muted">Acte p. ${au.pages[0]}–${au.pages[1]} · ${src(au.url, au.pages[0])}</p>` : ci ? `
      <p>${pill("cited", "preuve indirecte")}</p>
      <p>Acte n° <b class="num">${esc(ci.numero_acte)}</b> du ${fr(ci.date)} — original non trouvé, cité par un acte de 2025</p>
      <p>${benef ? `<b>${esc(benef.nom)}</b> <span class="muted small">${esc(benef.forme)}</span>` : ""}</p>
      <p class="small muted">${src(ci.url, ci.page)}</p>
      <details><summary>Où l'original a été cherché</summary><ul class="small muted">${(nt.autorisation || []).map(n => `<li>${esc(n)}</li>`).join("")}</ul></details>` : miss("autorisation")}</div>
  </div>`;
}

function criteria(fi) {
  const k = fi.avis?.criteres;
  if (!k) return "";
  const cats = Object.entries(k.par_categorie).sort((a, b) => b[1].points - a[1].points);
  const bars = cats.map(([cat, v]) => `<div class="bar ${cat === "implantation_immobilier" ? "hl" : ""}"
      data-tip="<b>${CAT[cat]}</b><br>${v.points} points sur ${k.total_points}">
      <span class="name">${CAT[cat]}</span><span class="track"><span class="fill" style="display:block;width:${v.pct}%"></span></span>
      <span class="val num">${pct(v.pct)} · ${v.points} / ${k.total_points} pts</span></div>`).join("");
  const im = k.par_categorie.implantation_immobilier, t = k.controle_total;
  const rows = k.criteres.map(c => `<tr><td>${esc(c.bloc)}</td><td>${esc(c.critere)}</td><td class="num">${c.coef}</td><td class="num">${c.points_max}</td><td>${esc(CAT[c.categorie])}</td><td>${src(c.url, c.page)}</td></tr>`).join("");
  return `<div class="criteria"><h3>Ce qui est noté — grille de sélection ramenée à 6 catégories</h3>
    <div class="bars">${bars}</div>
    <p class="callout">L'implantation et les locaux ne pèsent que <b>${pct(im.pct)}</b> de la note (${im.points} pts sur ${k.total_points}).
      ${t ? `${pill(t.statut === "ok" ? "ok" : "over", t.statut === "ok" ? "grille complète" : "écart")} Somme des coefficients lus : ${t.coef_lus}, pour un total imprimé de ${t.coef_annonce}.` : ""}</p>
    <details><summary>Détail des ${k.criteres.length} critères · extraction par ${k.methode === "regles" ? "règles" : esc(k.methode)}${k.llm ? " + LLM " + esc(k.llm.modele) : ""}</summary>
      <div class="scroll"><table><thead><tr><th>Bloc</th><th>Critère</th><th>Coef.</th><th>Points</th><th>Catégorie</th><th>Source</th></tr></thead><tbody>${rows}</tbody></table></div></details></div>`;
}

function card(fi) {
  const ctl = delai(fi);
  const ctlTxt = ctl?.statut === "ok" ? `autorisation le ${fr(ctl.date_autorisation)}, borne au ${fr(ctl.borne)}`
               : ctl?.statut === "dépassé" ? `autorisation le ${fr(ctl.date_autorisation)}, au-delà de la borne du ${fr(ctl.borne)}`
               : esc(ctl?.raison || "");
  const ben = fi.controles.find(c => c.regle.startsWith("bénéficiaire"));
  return `<article class="card" id="aap-${fi.aap_id}">
    <div class="fiche-head"><div><h3 style="font-size:1.1rem">AAP n° ${esc(fi.aap_id)}${fi.bonus ? '<span class="tag">bonus · sans recherche dédiée</span>' : ""}</h3>
      <p class="objet">${esc(fi.objet || "objet inconnu")}</p></div>${meter(fi.confiance)}</div>
    <div class="timeline" data-aap="${esc(fi.aap_id)}"></div>
    <div class="missing small">${pill(delaiState(fi), "délai ≤ 6 mois : " + ST[delaiState(fi)][2])} <span class="muted">${ctlTxt}</span>
      ${ben ? pill(ben.statut === "ok" ? "ok" : "over", "lauréat = bénéficiaire") : ""}
      ${["avis", "classement", "autorisation"].filter(k => docState(fi, k) === "missing").map(k => pill("missing", k + " non trouvé")).join(" ")}</div>
    ${docs(fi)}${criteria(fi)}</article>`;
}

function drawTimelines() {
  document.querySelectorAll(".timeline").forEach(el => {
    const fi = D.fiches.find(f => f.aap_id === el.dataset.aap);
    el.innerHTML = timeline(fi, el.clientWidth) || '<p class="small muted">Aucune date datable.</p>';
  });
}

// ---------- prospection
function prospection() {
  const laureats = D.fiches.flatMap(f => {
    const au = f.autorisation, ci = f.autorisation_citee, b = V(au, "beneficiaire") || ci?.beneficiaire;
    if (!b) return [];
    return [{ f, b, date: V(au, "date_autorisation") || ci.date, direct: !!au, url: au ? au.url : ci.url, page: au ? au.pages[0] : ci.page }];
  });
  const autres = D.fiches.flatMap(f => (V(f.classement, "classement") || []).filter(e => e.rang > 1)
    .map(e => ({ f, e, url: F(f.classement, "classement").url, page: F(f.classement, "classement").page })));
  const where = f => `${esc(TYPE(f.type))}${f.places ? " · " + f.places + " places" : ""} · ${esc(f.territoire || "?")}`;
  document.getElementById("prosp").innerHTML = `
    <p class="lede" style="margin:0 0 14px">Un AAP exécute une programmation publique : besoin (PRS, schémas départementaux, taux d'équipement)
      → annonce (calendrier prévisionnel) → avis, classement, autorisation → locaux. Les deux tableaux ci-dessous couvrent l'horizon <b>aval</b>,
      le seul alimenté par ce prototype.</p>
    <div class="card"><h3>Prospects en aval — lauréats autorisés</h3>
      <p class="small muted" style="margin:4px 0 10px">Une création ou une extension autorisée signifie souvent des locaux à trouver, aménager ou mettre en conformité avant la visite de conformité (CASF L313-6).</p>
      <div class="scroll"><table><thead><tr><th>Personne morale</th><th>Dispositif</th><th>AAP</th><th>Autorisé le</th><th>Preuve</th><th>Source</th></tr></thead><tbody>
      ${laureats.map(l => `<tr><td><b>${esc(l.b.nom)}</b><div class="small muted">${esc(l.b.forme)}</div></td><td>${where(l.f)}</td>
        <td><a href="#aap-${l.f.aap_id}">${esc(l.f.aap_id)}</a></td><td class="num">${fr(l.date)}</td>
        <td>${l.direct ? pill("found", "acte original") : pill("cited", "citée")}</td><td>${src(l.url, l.page)}</td></tr>`).join("")}
      </tbody></table></div></div>
    <div class="card"><h3>Projets prêts — candidats classés non retenus</h3>
      <p class="small muted" style="margin:4px 0 10px">Ils ont déjà monté un dossier sur ce territoire et le représenteront souvent au prochain appel.</p>
      <div class="scroll"><table><thead><tr><th>Personne morale</th><th>Rang</th><th>AAP</th><th>Dispositif</th><th>Commission</th><th>Source</th></tr></thead><tbody>
      ${autres.map(a => `<tr><td><b>${esc(a.e.nom)}</b><div class="small muted">${esc(a.e.forme)}</div></td><td class="num">${a.e.rang}${a.e.ex_aequo ? " ex æquo" : ""}</td>
        <td><a href="#aap-${a.f.aap_id}">${esc(a.f.aap_id)}</a></td><td>${where(a.f)}</td><td class="num">${fr(V(a.f.classement, "date_commission"))}</td><td>${src(a.url, a.page)}</td></tr>`).join("")}
      </tbody></table></div></div>
    <p class="small muted">Non fait : les horizons tendance (objectifs de places des PRS et schémas face aux places déjà autorisées)
      et annonce (calendriers prévisionnels). Voir la note, section 5.</p>`;
}

function footer() {
  document.getElementById("sources").innerHTML = `<h2>Sources parcourues</h2>
    <p class="muted">Généré le ${new Date(D.genere_le).toLocaleString("fr-FR")}. PDF téléchargés une seule fois (cache local), 2 s entre requêtes, User-Agent identifiable.
      Seules les personnes morales sont conservées ; un contrôle bloquant à l'export écarte tout nom de personne physique.</p>
    <ul>${D.sources.map(s => `<li><a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(short(s.url))}</a>
      <span class="muted">— ${s.pages || "?"} pages — ${esc((s.actes_retenus || []).join(" ; ") || "aucun acte retenu")}</span></li>`).join("")}</ul>
    <p class="muted">Autres n° d'AAP repérés en passant : ${esc(D.autres_aap_detectes.join(", ") || "aucun")}.</p>`;
}

kpis(); summary();
document.getElementById("cards").innerHTML = D.fiches.map(card).join("");
drawTimelines(); prospection(); footer();
let rz; addEventListener("resize", () => { clearTimeout(rz); rz = setTimeout(drawTimelines, 120); });
