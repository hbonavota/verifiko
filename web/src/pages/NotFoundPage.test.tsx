import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { I18nProvider } from "../lib/i18n";
import { NotFoundPage } from "./NotFoundPage";

function robotsMeta() {
  return document.head.querySelector('meta[name="robots"]');
}

describe("NotFoundPage", () => {
  it("marks the soft 404 as noindex while mounted and links back home", () => {
    const { unmount } = render(
      <MemoryRouter initialEntries={["/no-such-page"]}>
        <I18nProvider>
          <NotFoundPage />
        </I18nProvider>
      </MemoryRouter>,
    );

    expect(robotsMeta()).toHaveAttribute("content", "noindex");
    expect(document.title).toBe("Not Found | Verifiko");
    expect(screen.getByRole("link", { name: "Return to home" })).toHaveAttribute("href", "/");

    unmount();

    expect(robotsMeta()).toBeNull();
  });
});
