import { describe, expect, it } from "vitest";
import { ApiError, errorMessage, fieldIssues, readCookie } from "../lib/api";
import { languageFromQuery } from "../lib/lang";
import { LANGUAGES, tr } from "../lib/strings";

describe("translations", () => {
  it("returns the requested language", () => {
    expect(tr("hi", "search")).toBe("खोजें");
    expect(tr("ta", "search")).toBe("தேடு");
  });

  it("falls back to English for an unknown language", () => {
    expect(tr("bn" as never, "search")).toBe("Search");
  });

  it("returns the key when a string is missing instead of inventing text", () => {
    expect(tr("en", "not_a_real_key")).toBe("not_a_real_key");
  });

  it("offers exactly the supported languages", () => {
    expect(LANGUAGES.map((item) => item.code)).toEqual(["en", "hi", "ta"]);
  });

  it("keeps the independent-platform disclaimer in every language", () => {
    for (const { code } of LANGUAGES) {
      expect(tr(code, "independent_notice").toLowerCase()).toContain("hva");
    }
  });
});

describe("language selection", () => {
  it("honours a supported language in the URL", () => {
    expect(languageFromQuery("?language=hi")).toBe("hi");
    expect(languageFromQuery("?q=farmer&language=ta")).toBe("ta");
    expect(languageFromQuery("?language=en")).toBe("en");
  });

  it("ignores unsupported or absent URL languages", () => {
    expect(languageFromQuery("?language=bn")).toBeNull();
    expect(languageFromQuery("?language=")).toBeNull();
    expect(languageFromQuery("")).toBeNull();
  });
});

describe("api error handling", () => {
  it("exposes the API message and code", () => {
    const error = new ApiError(429, "rate_limited", "Too many attempts.");
    expect(errorMessage(error)).toBe("Too many attempts.");
    expect(error.code).toBe("rate_limited");
    expect(error.status).toBe(429);
  });

  it("never leaks a raw non-API error to the user unchanged", () => {
    expect(errorMessage("boom")).toBe("Something went wrong. Please try again.");
  });

  it("maps field issues without the body prefix", () => {
    const error = new ApiError(422, "validation_error", "Invalid input.", [
      { field: "body.phone", issue: "Enter a 10-digit Indian mobile number." },
      { field: "email", issue: "Enter a valid email address." },
      { issue: "ignored" },
    ]);
    expect(fieldIssues(error)).toEqual({
      phone: "Enter a 10-digit Indian mobile number.",
      email: "Enter a valid email address.",
    });
  });

  it("returns no field issues for network failures", () => {
    expect(fieldIssues(new ApiError(0, "network_error", "offline"))).toEqual({});
    expect(fieldIssues(new Error("x"))).toEqual({});
  });

  it("reads no cookie during server rendering", () => {
    expect(readCookie("hva_csrf")).toBeNull();
  });
});
