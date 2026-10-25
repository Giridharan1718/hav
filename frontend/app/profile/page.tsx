"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { api, errorMessage } from "@/lib/api";
import { useRequireAuth } from "@/components/useRequireAuth";
import { useAuth } from "@/components/AuthProvider";
import { Alert, Badge, Field, PageHeader, Spinner } from "@/components/ui";
import type { Address, Lang, PostalResponse, Profile } from "@/lib/types";

interface ProfilePayload {
  profile: Profile | null;
  address: Address | null;
  privacy: { note: string };
}

const emptyForm = {
  full_name: "",
  date_of_birth: "",
  preferred_language: "en" as Lang,
  phone: "",
  gender: "",
};

export default function ProfilePage() {
  const { me, loading } = useRequireAuth();
  const { refresh } = useAuth();
  const [payload, setPayload] = useState<ProfilePayload | null>(null);
  const [form, setForm] = useState(emptyForm);
  const [addressForm, setAddressForm] = useState({ line1: "", pincode: "", post_office: "", district: "", state: "" });
  const [lookup, setLookup] = useState<PostalResponse | null>(null);
  const [lookupError, setLookupError] = useState<string | null>(null);
  const [lookupBusy, setLookupBusy] = useState(false);
  const [saveBusy, setSaveBusy] = useState(false);
  const [addressBusy, setAddressBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [warnings, setWarnings] = useState<string[]>([]);

  const [challengeSent, setChallengeSent] = useState(false);
  const [devCode, setDevCode] = useState<string | null>(null);
  const [otp, setOtp] = useState("");
  const [phoneBusy, setPhoneBusy] = useState(false);
  const [phoneNotice, setPhoneNotice] = useState<string | null>(null);
  const [phoneError, setPhoneError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const data = await api<ProfilePayload>("/me/profile");
      setPayload(data);
      setForm({
        full_name: data.profile?.full_name ?? "",
        date_of_birth: data.profile?.date_of_birth ?? "",
        preferred_language: (data.profile?.preferred_language as Lang) ?? "en",
        phone: data.profile?.phone ?? "",
        gender: data.profile?.gender ?? "",
      });
      setAddressForm({
        line1: data.address?.line1 ?? "",
        pincode: data.address?.pincode ?? "",
        post_office: data.address?.post_office ?? "",
        district: data.address?.district ?? "",
        state: data.address?.state ?? "",
      });
    } catch (err) {
      setError(err);
    }
  }, []);

  useEffect(() => {
    if (me) void load();
  }, [me, load]);

  async function saveProfile(event: React.FormEvent) {
    event.preventDefault();
    setSaveBusy(true);
    setError(null);
    setNotice(null);
    try {
      await api<ProfilePayload>("/me/profile", {
        method: "PUT",
        json: {
          full_name: form.full_name,
          date_of_birth: form.date_of_birth || null,
          preferred_language: form.preferred_language,
          phone: form.phone || null,
          gender: form.gender || null,
        },
      });
      await load();
      await refresh();
      setNotice("Profile saved. Changing your phone number resets its verification.");
    } catch (err) {
      setError(err);
    } finally {
      setSaveBusy(false);
    }
  }

  async function findPostOffices() {
    if (!/^[1-9][0-9]{5}$/.test(addressForm.pincode)) {
      setLookupError("Enter a six-digit PIN code that does not start with zero.");
      setLookup(null);
      return;
    }
    setLookupBusy(true);
    setLookupError(null);
    setLookup(null);
    try {
      const response = await api<PostalResponse>(`/postal/${addressForm.pincode}`);
      setLookup(response);
      if (response.matches.length === 1) {
        setAddressForm((current) => ({
          ...current,
          post_office: response.matches[0].name,
          district: response.matches[0].district,
          state: response.matches[0].state,
        }));
      }
    } catch (err) {
      setLookupError(errorMessage(err));
    } finally {
      setLookupBusy(false);
    }
  }

  function choosePostOffice(name: string) {
    const match = lookup?.matches.find((item) => item.name === name);
    if (!match) return;
    setAddressForm((current) => ({
      ...current,
      post_office: match.name,
      district: match.district,
      state: match.state,
    }));
  }

  async function saveAddress(event: React.FormEvent) {
    event.preventDefault();
    setAddressBusy(true);
    setError(null);
    setNotice(null);
    setWarnings([]);
    try {
      const result = await api<ProfilePayload & { warnings?: Array<{ message: string }> }>("/me/address", {
        method: "PUT",
        json: {
          line1: addressForm.line1 || null,
          pincode: addressForm.pincode,
          post_office: addressForm.post_office || null,
          district: addressForm.district || null,
          state: addressForm.state || null,
          post_office_confirmed: Boolean(addressForm.post_office && lookup?.matches.some((item) => item.name === addressForm.post_office)),
        },
      });
      setPayload(result);
      setWarnings((result.warnings ?? []).map((item) => item.message));
      setNotice("Address saved.");
      await refresh();
    } catch (err) {
      setError(err);
    } finally {
      setAddressBusy(false);
    }
  }

  async function deleteProfileData() {
    if (!window.confirm("Delete your profile and address? Drafts are kept. This cannot be undone.")) return;
    setError(null);
    try {
      await api("/me/profile", { method: "DELETE" });
      await load();
      await refresh();
      setNotice("Profile and address deleted.");
    } catch (err) {
      setError(err);
    }
  }

  async function sendChallenge() {
    setPhoneBusy(true);
    setPhoneError(null);
    setPhoneNotice(null);
    try {
      const result = await api<{ phone_masked: string; dev_code: string | null; delivery: string }>(
        "/auth/phone/challenge",
        { method: "POST", json: { phone: form.phone } },
      );
      setChallengeSent(true);
      setDevCode(result.dev_code);
      setPhoneNotice(`Code sent to ${result.phone_masked} via ${result.delivery}.`);
    } catch (err) {
      setPhoneError(errorMessage(err));
    } finally {
      setPhoneBusy(false);
    }
  }

  async function verifyPhone() {
    setPhoneBusy(true);
    setPhoneError(null);
    try {
      await api("/auth/phone/verify", { method: "POST", json: { code: otp } });
      setChallengeSent(false);
      setDevCode(null);
      setOtp("");
      setPhoneNotice("Phone verified. This confirms access to the number, not your legal identity.");
      await load();
      await refresh();
    } catch (err) {
      setPhoneError(errorMessage(err));
    } finally {
      setPhoneBusy(false);
    }
  }

  if (loading) return <div className="card">Loading your profile…</div>;
  if (!me) return <div className="card">Redirecting to sign in…</div>;
  if (!payload && !error) return <div className="card"><Spinner label="Loading profile…" /></div>;

  const phoneVerified = payload?.profile?.phone_verified ?? false;
  const postOffices = lookup?.matches ?? [];

  return (
    <>
      <PageHeader
        title="Profile and address"
        lead="Only provide what you need. Each field explains why it is asked for, and all of it can be deleted."
        actions={<Link href="/settings/privacy" className="btn btn-ghost">Privacy settings</Link>}
      />
      {error ? <Alert tone="danger" title="Could not save">{errorMessage(error)}</Alert> : null}
      {notice ? <Alert tone="success">{notice}</Alert> : null}
      {warnings.map((warning) => (
        <Alert key={warning} tone="warning">{warning}</Alert>
      ))}

      <div className="grid-2">
        <section className="card">
          <h2 style={{ marginTop: 0 }}>About you</h2>
          <p className="small muted">{payload?.privacy.note}</p>
          <form onSubmit={saveProfile}>
            <Field id="full_name" label="Full name" required hint="Any Indian script is accepted. This is a display name, not a verified identity.">
              <input
                id="full_name"
                className="input"
                value={form.full_name}
                onChange={(event) => setForm({ ...form, full_name: event.target.value })}
                required
                minLength={2}
              />
            </Field>
            <Field id="dob" label="Date of birth" hint="Optional. Used for age-based criteria; stored encrypted and never shown to other users.">
              <input
                id="dob"
                className="input"
                type="date"
                value={form.date_of_birth}
                onChange={(event) => setForm({ ...form, date_of_birth: event.target.value })}
              />
            </Field>
            <Field id="gender" label="Gender" hint="Optional. Asked only because a few schemes are gender-specific; not used for anything else.">
              <select
                id="gender"
                className="select"
                value={form.gender}
                onChange={(event) => setForm({ ...form, gender: event.target.value })}
              >
                <option value="">Prefer not to say</option>
                <option value="female">Female</option>
                <option value="male">Male</option>
                <option value="other">Other</option>
              </select>
            </Field>
            <Field id="language" label="Preferred language">
              <select
                id="language"
                className="select"
                value={form.preferred_language}
                onChange={(event) => setForm({ ...form, preferred_language: event.target.value as Lang })}
              >
                <option value="en">English</option>
                <option value="hi">हिन्दी</option>
                <option value="ta">தமிழ்</option>
              </select>
            </Field>
            <Field
              id="phone"
              label="Mobile number"
              hint="Optional. Changing it removes the verified status. Verification proves access to the number, not legal identity."
            >
              <input
                id="phone"
                className="input"
                inputMode="tel"
                placeholder="9876543210"
                value={form.phone}
                onChange={(event) => setForm({ ...form, phone: event.target.value })}
              />
            </Field>
            <div className="row">
              <button type="submit" className="btn btn-primary" disabled={saveBusy}>
                {saveBusy ? "Saving…" : "Save profile"}
              </button>
              <button type="button" className="btn btn-ghost" onClick={() => void deleteProfileData()}>
                Delete profile and address
              </button>
            </div>
          </form>
        </section>

        <section className="card">
          <h2 style={{ marginTop: 0 }}>Phone verification</h2>
          <p className="small">
            Status:{" "}
            {phoneVerified ? (
              <Badge tone="ok">verified</Badge>
            ) : (
              <Badge tone="warn">not verified</Badge>
            )}
          </p>
          {phoneNotice ? <Alert tone="success">{phoneNotice}</Alert> : null}
          {phoneError ? <Alert tone="danger">{phoneError}</Alert> : null}
          {form.phone ? (
            challengeSent ? (
              <div>
                {devCode ? (
                  <Alert tone="warning" title="Development delivery only">
                    The mock SMS adapter did not send a real message. Development code:{" "}
                    <strong>{devCode}</strong>. This is never returned in production.
                  </Alert>
                ) : null}
                <Field id="otp" label="Enter the 6-digit code" required>
                  <input
                    id="otp"
                    className="input"
                    inputMode="numeric"
                    value={otp}
                    onChange={(event) => setOtp(event.target.value.replace(/\D/g, "").slice(0, 6))}
                    autoComplete="one-time-code"
                  />
                </Field>
                <div className="row">
                  <button type="button" className="btn btn-primary" disabled={phoneBusy || otp.length !== 6} onClick={() => void verifyPhone()}>
                    Verify phone
                  </button>
                  <button type="button" className="btn btn-secondary" disabled={phoneBusy} onClick={() => void sendChallenge()}>
                    Resend code
                  </button>
                </div>
              </div>
            ) : (
              <button type="button" className="btn btn-secondary" onClick={() => void sendChallenge()} disabled={phoneBusy}>
                {phoneBusy ? "Sending…" : "Send verification code"}
              </button>
            )
          ) : (
            <p className="small muted">Save a mobile number to start verification.</p>
          )}
        </section>
      </div>

      <section className="card" style={{ marginTop: "1rem" }}>
        <h2 style={{ marginTop: 0 }}>Address and PIN code</h2>
        <p className="small muted">
          The PIN code is checked against a small development postal sample. If it is unknown or covers
          several post offices, you will be asked to choose; the district and state are only filled from
          a post office you select.
        </p>
        <form onSubmit={saveAddress}>
          <div className="inline-form">
            <Field id="pincode" label="PIN code" required hint="Six digits, cannot start with zero.">
              <input
                id="pincode"
                className="input"
                inputMode="numeric"
                value={addressForm.pincode}
                onChange={(event) => {
                  setAddressForm({
                    ...addressForm,
                    pincode: event.target.value.replace(/\D/g, "").slice(0, 6),
                    post_office: "",
                    district: "",
                    state: "",
                  });
                  setLookup(null);
                }}
                required
                pattern="[1-9][0-9]{5}"
              />
            </Field>
            <button type="button" className="btn btn-secondary" onClick={() => void findPostOffices()} disabled={lookupBusy}>
              {lookupBusy ? "Looking up…" : "Find post offices"}
            </button>
          </div>
          {lookupError ? <Alert tone="warning">{lookupError}</Alert> : null}
          {postOffices.length > 0 ? (
            <fieldset>
              <legend>Choose your post office</legend>
              {postOffices.map((office) => (
                <div key={`${office.name}-${office.district}`} className="check">
                  <input
                    type="radio"
                    id={`po-${office.name}`}
                    name="post_office"
                    checked={addressForm.post_office === office.name}
                    onChange={() => choosePostOffice(office.name)}
                  />
                  <label htmlFor={`po-${office.name}`}>
                    {office.name} · {office.district}, {office.state}
                    {office.branch_type ? <span className="muted small"> · {office.branch_type}</span> : null}
                  </label>
                </div>
              ))}
              {lookup?.source.is_sample ? (
                <p className="small muted">
                  Postal dataset: development sample, retrieved{" "}
                  {lookup.source.retrieved_at ? new Date(lookup.source.retrieved_at).toLocaleDateString() : "unknown"}.
                  Confirm against the official India Post directory before relying on it.
                </p>
              ) : null}
            </fieldset>
          ) : null}
          <Field id="line1" label="Address line" hint="House or street details. Optional.">
            <input
              id="line1"
              className="input"
              value={addressForm.line1}
              onChange={(event) => setAddressForm({ ...addressForm, line1: event.target.value })}
            />
          </Field>
          <div className="grid-2">
            <Field id="district" label="District" hint="Only used if a scheme is district-specific.">
              <input
                id="district"
                className="input"
                value={addressForm.district}
                onChange={(event) => setAddressForm({ ...addressForm, district: event.target.value })}
              />
            </Field>
            <Field id="state" label="State or UT">
              <input
                id="state"
                className="input"
                value={addressForm.state}
                onChange={(event) => setAddressForm({ ...addressForm, state: event.target.value })}
              />
            </Field>
          </div>
          <div className="row">
            <button type="submit" className="btn btn-primary" disabled={addressBusy}>
              {addressBusy ? "Saving…" : "Save address"}
            </button>
            {payload?.address ? (
              <span className="small">
                Saved: {payload.address.pincode}
                {payload.address.post_office ? ` · ${payload.address.post_office}` : ""}{" "}
                {payload.address.post_office_confirmed ? (
                  <Badge tone="ok">post office confirmed</Badge>
                ) : (
                  <Badge tone="warn">not confirmed</Badge>
                )}
              </span>
            ) : null}
          </div>
        </form>
      </section>
    </>
  );
}
