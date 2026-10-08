// ESLint flat config (eslint 9). Next 16 removed `next lint`, so the lab app
// lints via the ESLint CLI against the Next-recommended rules.
import nextCoreWebVitals from "eslint-config-next/core-web-vitals";

const config = [
  ...nextCoreWebVitals,
  {
    ignores: [".next/**", "node_modules/**", "next-env.d.ts"],
  },
];

export default config;
