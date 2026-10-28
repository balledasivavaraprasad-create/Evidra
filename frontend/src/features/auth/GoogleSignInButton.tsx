import React, { useEffect, useRef, useState } from "react";

interface GoogleCredentialResponse {
  credential: string;
}

interface GoogleIdentity {
  accounts: {
    id: {
      initialize: (config: {
        client_id: string;
        callback: (response: GoogleCredentialResponse) => void;
        ux_mode?: "popup" | "redirect";
        auto_select?: boolean;
      }) => void;
      renderButton: (
        parent: HTMLElement,
        options: {
          type?: "standard" | "icon";
          theme?: "outline" | "filled_blue" | "filled_black";
          size?: "large" | "medium" | "small";
          text?: "signin_with" | "signup_with" | "continue_with";
          shape?: "rectangular" | "pill";
          width?: number;
          logo_alignment?: "left" | "center";
        },
      ) => void;
    };
  };
}

declare global {
  interface Window {
    google?: GoogleIdentity;
  }
}

const GIS_SRC = "https://accounts.google.com/gsi/client";
let gisLoader: Promise<void> | null = null;

function loadGoogleIdentity(): Promise<void> {
  if (window.google?.accounts?.id) return Promise.resolve();
  if (!gisLoader) {
    gisLoader = new Promise((resolve, reject) => {
      const script = document.createElement("script");
      script.src = GIS_SRC;
      script.async = true;
      script.defer = true;
      script.onload = () => resolve();
      script.onerror = () => {
        gisLoader = null;
        reject(new Error("Couldn't load Google sign-in"));
      };
      document.head.appendChild(script);
    });
  }
  return gisLoader;
}

/** Google's own "Continue with Google" button; hands the ID token to onCredential. */
export const GoogleSignInButton: React.FC<{
  clientId: string;
  text: "signin_with" | "signup_with" | "continue_with";
  onCredential: (credential: string) => void;
}> = ({ clientId, text, onCredential }) => {
  const container = useRef<HTMLDivElement>(null);
  const callbackRef = useRef(onCredential);
  callbackRef.current = onCredential;
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    loadGoogleIdentity()
      .then(() => {
        if (cancelled || !container.current || !window.google) return;
        window.google.accounts.id.initialize({
          client_id: clientId,
          callback: (res) => callbackRef.current(res.credential),
          ux_mode: "popup",
        });
        container.current.innerHTML = "";
        window.google.accounts.id.renderButton(container.current, {
          type: "standard",
          theme: document.documentElement.classList.contains("dark") ? "filled_black" : "outline",
          size: "large",
          text,
          shape: "rectangular",
          width: Math.min(container.current.clientWidth || 360, 400),
          logo_alignment: "center",
        });
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      });
    return () => {
      cancelled = true;
    };
  }, [clientId, text]);

  if (failed) {
    return (
      <p className="text-xs text-center text-[var(--text-muted)]">
        Google sign-in couldn't load. Check your connection or use email instead.
      </p>
    );
  }
  return <div ref={container} className="flex justify-center min-h-[44px]" aria-label="Continue with Google" />;
};
