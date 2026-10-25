// The /vitest entry registers the matchers on Vitest's expect and types them;
// the bare "@testing-library/jest-dom" import expects a global expect (globals: true).
import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

// Testing Library only auto-cleans up when afterEach is a global.
afterEach(() => {
  cleanup();
});
