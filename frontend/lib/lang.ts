"use client";

import { useEffect, useState } from "react";
import type { Lang } from "./types";
import { readCookie } from "./api";

export const LANG_COOKIE = "hva_lang";
const VALID: Lang[] = ["en", "hi", "ta"];
const EVENT = "hva:lang";

export function getLang(): Lang {
  const value = readCookie(LANG_COOKIE) as Lang | null;
  return value && VALID.includes(value) ? value : "en";
}

export function languageFromQuery(search: string): Lang | null {
  const value = new URLSearchParams(search).get("language") as Lang | null;
  return value && VALID.includes(value) ? value : null;
}

export function setLang(lang: Lang): void {
  document.cookie = `${LANG_COOKIE}=${lang}; Path=/; Max-Age=31536000; SameSite=Lax`;
  document.documentElement.lang = lang;
  window.dispatchEvent(new Event(EVENT));
}

export function useLang(): Lang {
  const [lang, set] = useState<Lang>("en");
  useEffect(() => {
    const fromUrl = languageFromQuery(window.location.search);
    if (fromUrl) {
      // A shared or bookmarked ?language= link wins over the existing cookie.
      setLang(fromUrl);
      set(fromUrl);
    } else {
      set(getLang());
    }
    const handler = () => set(getLang());
    window.addEventListener(EVENT, handler);
    window.addEventListener("focus", handler);
    return () => {
      window.removeEventListener(EVENT, handler);
      window.removeEventListener("focus", handler);
    };
  }, []);
  return lang;
}

export function useOnline(): boolean {
  const [online, setOnline] = useState(true);
  useEffect(() => {
    const update = () => setOnline(navigator.onLine);
    update();
    window.addEventListener("online", update);
    window.addEventListener("offline", update);
    return () => {
      window.removeEventListener("online", update);
      window.removeEventListener("offline", update);
    };
  }, []);
  return online;
}
