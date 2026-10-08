// UI↔API contract smoke test: verifies that every endpoint the lab pages call
// returns the fields the components actually read. Run with the API up:
//   node scripts/smoke-api.mjs
const BASE = process.env.ORIGIN_API || "http://127.0.0.1:8788";

async function get(path) {
  const r = await fetch(`${BASE}${path}`);
  if (!r.ok) throw new Error(`${path} -> ${r.status}`);
  return r.json();
}

const checks = [];
function ok(name, cond, extra = "") {
  checks.push({ name, pass: !!cond, extra });
}

const exps = await get("/api/experiments");
ok("experiments is array", Array.isArray(exps));
ok("experiment has summary", exps.length === 0 || typeof exps[0].summary?.n_done === "number");
const expId = exps[0]?.id;

const protocols = await get("/api/protocols");
ok("protocols is array", Array.isArray(protocols));
ok("protocol carries config", protocols.length === 0 || typeof protocols[0].config === "object");

if (expId) {
  const detail = await get(`/api/experiments/${expId}`);
  ok("detail.trials array", Array.isArray(detail.trials));
  ok("detail.summary", typeof detail.summary?.n_done === "number");

  const cmp = await get(`/api/compare?experiment=${expId}`);
  ok("compare.comparison object", typeof cmp.comparison === "object");
  const firstAlgo = Object.keys(cmp.comparison)[0];
  ok("compare entry shape", firstAlgo && "test_mean_reward" in cmp.comparison[firstAlgo]);

  const arts = await get(`/api/artifacts?experiment=${expId}`);
  ok("artifacts array", Array.isArray(arts));

  const fails = await get(`/api/failures`);
  ok("failures array", Array.isArray(fails));
}

// Viewer contracts, covered once per experiment kind present in the store:
// a grid trial must return a real replay payload; an embodied trial must retain
// the structured /api/world 4xx (it is not a grid), while /api/morphology
// exposes the persisted body plan without fabricating a physics replay.
let gridWorldChecked = false;
let embodiedWorldChecked = false;
for (const e of exps) {
  if (gridWorldChecked && embodiedWorldChecked) break;
  const detail = await get(`/api/experiments/${e.id}`);
  const kind = JSON.parse(detail.experiment.config_json).env_kind || "gridworld";
  const trial = detail.trials.find(
    (t) => t.status === "done" && !["random", "heuristic"].includes(t.algorithm)
  );
  if (!trial) continue;
  const r = await fetch(`${BASE}/api/world?experiment=${e.id}&trial=${trial.id}&seed=101`);
  if (kind === "gridworld" && !gridWorldChecked) {
    ok("world responds 200 for a grid trial", r.ok);
    const w = await r.json();
    ok("world.grid rectangular", Array.isArray(w.grid) && Array.isArray(w.grid[0]));
    ok("world.trajectory non-empty", Array.isArray(w.trajectory) && w.trajectory.length > 0);
    ok("world.morphology present", typeof w.morphology === "object");
    gridWorldChecked = true;
  } else if (kind !== "gridworld" && !embodiedWorldChecked) {
    ok(`world degrades gracefully for ${kind} trials`, r.status === 400);
    const body = await r.json();
    ok("world degradation names the reason", typeof body.error === "string" && body.error.includes("gridworld"));
    const morphology = await get(`/api/morphology?experiment=${e.id}&trial=${trial.id}`);
    ok("morphology plan exposes embodied body", morphology.viewer_kind === "morphology_plan");
    ok("morphology plan is not a replay", morphology.physics_replay === false);
    ok("morphology plan has links and joints", Array.isArray(morphology.body?.segments) && Array.isArray(morphology.body?.joints));
    ok("morphology plan exposes calibration gate", morphology.calibration?.status === "required");
    embodiedWorldChecked = true;
  }
}

let failed = 0;
for (const c of checks) {
  if (!c.pass) failed++;
  console.log(`${c.pass ? "PASS" : "FAIL"}  ${c.name}${c.extra ? "  " + c.extra : ""}`);
}
console.log(`\n${checks.length - failed}/${checks.length} checks passed`);
process.exit(failed ? 1 : 0);
