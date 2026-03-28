/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string;
  readonly VITE_GOOGLE_CLIENT_ID?: string;
}

interface GoogleIdentityCredentialResponse {
  credential?: string;
}

interface GoogleIdentityButtonConfiguration {
  theme?: "outline" | "filled_blue" | "filled_black";
  size?: "large" | "medium" | "small";
  shape?: "rectangular" | "pill" | "circle" | "square";
  text?: "signin_with" | "signup_with" | "continue_with" | "signin";
  locale?: string;
}

interface GoogleIdentityInitializeConfiguration {
  client_id: string;
  callback: (response: GoogleIdentityCredentialResponse) => void;
  ux_mode?: "popup" | "redirect";
  auto_select?: boolean;
  cancel_on_tap_outside?: boolean;
}

interface Window {
  __verifikoAnalyticsConfigured?: boolean;
  __verifikoLastPageViewKey?: string;
  dataLayer?: unknown[];
  gtag?: (...args: unknown[]) => void;
  google?: {
    accounts: {
      id: {
        initialize: (options: GoogleIdentityInitializeConfiguration) => void;
        renderButton: (parent: HTMLElement, options: GoogleIdentityButtonConfiguration) => void;
      };
    };
  };
}
