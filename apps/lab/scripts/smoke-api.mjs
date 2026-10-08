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

  const fails = await get("/api/failures");
  ok("failures array", Array.isArray(fails));

  // world viewer needs a trained (non-baseline) done trial
  const trial = detail.trials.find(
    (t) => t.status === "done" && !["random", "heuristic"].includes(t.algorithm)
  );
  if (trial) {
    const w = await get(`/api/world?experiment=${expId}&trial=${trial.id}&seed=101`);
    ok("world.grid rectangular", Array.isArray(w.grid) && Array.isArray(w.grid[0]));
    ok("world.trajectory non-empty", Array.isArray(w.trajectory) && w.trajectory.length > 0);
    ok("world.morphology present", typeof w.morphology === "object");
  }
}

let failed = 0;
for (const c of checks) {
  if (!c.pass) failed++;
  console.log(`${c.pass ? "PASS" : "FAIL"}  ${c.name}${c.extra ? "  " + c.extra : ""}`);
}
console.log(`\n${checks.length - failed}/${checks.length} checks passed`);
process.exit(failed ? 1 : 0);
