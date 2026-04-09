"use strict";

const fs = require("fs");

for (const name of ["package-lock.json", "yarn.lock"]) {
  try {
    if (fs.existsSync(name)) {
      fs.unlinkSync(name);
    }
  } catch {
    // ignore
  }
}

const ua = process.env.npm_config_user_agent ?? "";
if (!ua.includes("pnpm/")) {
  console.error("Use pnpm instead of npm/yarn for this workspace.");
  process.exit(1);
}
