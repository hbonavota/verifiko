import { registerSW } from "virtual:pwa-register";

import "./pwa.css";

// Loaded only when the build has VITE_PWA_ENABLED=true (see main.tsx).
const COPY = {
  en: { message: "A new version of Verifiko is available.", reload: "Reload", later: "Later" },
  es: {
    message: "Hay una nueva versión de Verifiko disponible.",
    reload: "Recargar",
    later: "Más tarde",
  },
} as const;

export function registerPwa(): void {
  const updateServiceWorker = registerSW({
    // registerType "prompt": a new worker waits until the user chooses to reload, so
    // the running page never has its shell or chunks swapped underneath it.
    onNeedRefresh() {
      showUpdatePrompt(() => {
        void updateServiceWorker(true);
      });
    },
    onRegisterError(error) {
      console.error("[pwa] Service worker registration failed.", error);
    },
  });
}

function showUpdatePrompt(onReload: () => void): void {
  if (document.querySelector(".pwa-update")) {
    return;
  }
  const copy = document.documentElement.lang.startsWith("es") ? COPY.es : COPY.en;

  const prompt = document.createElement("div");
  prompt.className = "pwa-update";
  prompt.setAttribute("role", "status");

  const message = document.createElement("p");
  message.className = "pwa-update__message";
  message.textContent = copy.message;

  const reload = document.createElement("button");
  reload.type = "button";
  reload.className = "button button--primary pwa-update__button";
  reload.textContent = copy.reload;
  reload.addEventListener("click", () => {
    reload.disabled = true;
    onReload();
  });

  const later = document.createElement("button");
  later.type = "button";
  later.className = "button button--ghost pwa-update__button";
  later.textContent = copy.later;
  later.addEventListener("click", () => prompt.remove());

  const actions = document.createElement("div");
  actions.className = "pwa-update__actions";
  actions.append(reload, later);
  prompt.append(message, actions);
  document.body.append(prompt);
}
