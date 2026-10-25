"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "./AuthProvider";
import type { Me } from "@/lib/types";

export function useRequireAuth(): { me: Me | null; loading: boolean } {
  const { me, loading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!loading && me === null) {
      router.replace(`/login?next=${encodeURIComponent(pathname)}`);
    }
  }, [loading, me, pathname, router]);

  return { me, loading };
}
