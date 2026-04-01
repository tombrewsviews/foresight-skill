"""Phase 1: Generate 60 synthetic test cases (12 per stratum × 5 strata)."""
import json
import os
import sys

BENCHMARK_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEST_CASES_DIR = os.path.join(BENCHMARK_DIR, "data", "test_cases")

STRATA = {
    "A": {"change_type": "bug_fix", "language": "typescript", "difficulty": "easy",
          "desc": "Bug fix — wrong return type"},
    "B": {"change_type": "feature_add", "language": "typescript", "difficulty": "medium",
          "desc": "Feature add — new async function"},
    "C": {"change_type": "refactor", "language": "python", "difficulty": "medium",
          "desc": "Refactor — extract shared utility"},
    "D": {"change_type": "schema_change", "language": "typescript", "difficulty": "hard",
          "desc": "Schema/type change"},
    "E": {"change_type": "architecture_shift", "language": "python", "difficulty": "hard",
          "desc": "Architecture shift — move logic between layers"},
}

# 12 cases per stratum. Each entry: (description, before_code, after_code, diff_summary, ground_truth)
CASES = {
"A": [
  {
    "description": "getUserAge returns string instead of number",
    "before_code": """// user-utils.ts
export interface User {
  id: string;
  name: string;
  birthYear: number;
}

export function getUserAge(user: User): number {
  return new Date().getFullYear() - user.birthYear;
}

export function canVote(user: User): boolean {
  return getUserAge(user) >= 18;
}""",
    "after_code": """// user-utils.ts
export interface User {
  id: string;
  name: string;
  birthYear: number;
}

export function getUserAge(user: User): string {
  return String(new Date().getFullYear() - user.birthYear);
}

export function canVote(user: User): boolean {
  return getUserAge(user) >= 18;
}""",
    "diff_summary": "Changed getUserAge return type from number to string",
    "ground_truth": {
      "will_break": ["canVote() compares string >= 18 — always false in strict mode, TS error on comparison"],
      "edge_cases": ["String comparison '9' >= '18' returns true due to lexicographic ordering"],
      "broken_pattern": "getUserAge previously returned a number like all other numeric utility functions; now returns string inconsistently",
      "next_prompt": "Why is canVote always returning false even for users over 18?",
      "verified_by": "injected_bug",
      "notes": "String-to-number comparison bug injected deliberately"
    },
    "token_cost_manual_followup": 0
  },
  {
    "description": "getDiscount returns undefined instead of 0 for non-members",
    "before_code": """// pricing.ts
export type MemberTier = 'basic' | 'premium' | 'vip';

export function getDiscount(tier: MemberTier | null): number {
  if (tier === 'vip') return 0.3;
  if (tier === 'premium') return 0.15;
  if (tier === 'basic') return 0.05;
  return 0;
}

export function getFinalPrice(price: number, tier: MemberTier | null): number {
  return price * (1 - getDiscount(tier));
}""",
    "after_code": """// pricing.ts
export type MemberTier = 'basic' | 'premium' | 'vip';

export function getDiscount(tier: MemberTier | null): number | undefined {
  if (tier === 'vip') return 0.3;
  if (tier === 'premium') return 0.15;
  if (tier === 'basic') return 0.05;
}

export function getFinalPrice(price: number, tier: MemberTier | null): number {
  return price * (1 - getDiscount(tier));
}""",
    "diff_summary": "getDiscount return type widened to number | undefined; removed fallback return 0",
    "ground_truth": {
      "will_break": ["getFinalPrice: 1 - undefined = NaN for non-member users; TS error on arithmetic with undefined"],
      "edge_cases": ["null tier (guest checkout) now returns NaN price silently"],
      "broken_pattern": "getDiscount lost its exhaustive return guarantee; callers assumed number, not number | undefined",
      "next_prompt": "Checkout total shows NaN for guest users",
      "verified_by": "injected_bug",
      "notes": "Removed default return, widened type — classic 'forgot the else'"
    },
    "token_cost_manual_followup": 0
  },
  {
    "description": "formatCurrency incorrectly divides by 100 always",
    "before_code": """// format.ts
export function formatCurrency(cents: number, currency = 'USD'): string {
  const dollars = cents / 100;
  return new Intl.NumberFormat('en-US', { style: 'currency', currency }).format(dollars);
}

export function formatLineItem(label: string, cents: number): string {
  return `${label}: ${formatCurrency(cents)}`;
}""",
    "after_code": """// format.ts
export function formatCurrency(amount: number, currency = 'USD'): string {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency }).format(amount);
}

export function formatLineItem(label: string, cents: number): string {
  return `${label}: ${formatCurrency(cents)}`;
}""",
    "diff_summary": "formatCurrency parameter renamed from cents to amount and division by 100 removed",
    "ground_truth": {
      "will_break": ["formatLineItem still passes cents to formatCurrency — displays 100x the correct amount (e.g. $9999.00 instead of $99.99)"],
      "edge_cases": ["Any caller passing cents (not dollars) now shows inflated prices silently"],
      "broken_pattern": "Function semantics changed from cents-in to dollars-in without updating callers or renaming the parameter at call sites",
      "next_prompt": "Prices in the cart are showing 100 times the expected amount",
      "verified_by": "injected_bug",
      "notes": "Classic unit mismatch — changed the contract without updating callers"
    },
    "token_cost_manual_followup": 0
  },
  {
    "description": "isValidEmail regex accidentally inverted",
    "before_code": """// validation.ts
export function isValidEmail(email: string): boolean {
  const pattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return pattern.test(email);
}

export function validateFormField(field: string, value: string): string | null {
  if (field === 'email' && !isValidEmail(value)) {
    return 'Invalid email address';
  }
  return null;
}""",
    "after_code": """// validation.ts
export function isValidEmail(email: string): boolean {
  const pattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return !pattern.test(email);
}

export function validateFormField(field: string, value: string): string | null {
  if (field === 'email' && !isValidEmail(value)) {
    return 'Invalid email address';
  }
  return null;
}""",
    "diff_summary": "isValidEmail now returns !pattern.test(email) instead of pattern.test(email)",
    "ground_truth": {
      "will_break": ["validateFormField accepts all invalid emails and rejects all valid ones — form signup broken for every user"],
      "edge_cases": ["Empty string and malformed input now pass validation"],
      "broken_pattern": "Boolean return inverted silently — no type error, no test would catch unless testing both valid and invalid inputs",
      "next_prompt": "Users can't sign up — valid emails are being rejected",
      "verified_by": "injected_bug",
      "notes": "! operator added to return — silent logic inversion"
    },
    "token_cost_manual_followup": 0
  },
  {
    "description": "parseDate returns Invalid Date for valid ISO strings",
    "before_code": """// date-utils.ts
export function parseDate(input: string): Date {
  return new Date(input);
}

export function isExpired(isoDate: string): boolean {
  const date = parseDate(isoDate);
  return date.getTime() < Date.now();
}""",
    "after_code": """// date-utils.ts
export function parseDate(input: string): Date {
  const [year, month, day] = input.split('-').map(Number);
  return new Date(year, month, day);
}

export function isExpired(isoDate: string): boolean {
  const date = parseDate(isoDate);
  return date.getTime() < Date.now();
}""",
    "diff_summary": "parseDate changed from new Date(input) to manual year/month/day split",
    "ground_truth": {
      "will_break": ["Month is 1-indexed in ISO but 0-indexed in new Date(year, month, day) — all dates off by one month; isExpired returns wrong results"],
      "edge_cases": ["Input with time component (e.g. '2024-01-15T10:00:00Z') loses time info; datetime comparisons wrong"],
      "broken_pattern": "Replaced a standard Date constructor with manual parsing that has known gotchas (month indexing); doesn't match rest of codebase",
      "next_prompt": "Subscription expiry checks are failing — expired subscriptions showing as active",
      "verified_by": "injected_bug",
      "notes": "month indexing off-by-one is a classic JS Date trap"
    },
    "token_cost_manual_followup": 0
  },
  {
    "description": "sumArray uses wrong accumulator initial value",
    "before_code": """// math-utils.ts
export function sumArray(nums: number[]): number {
  return nums.reduce((acc, n) => acc + n, 0);
}

export function average(nums: number[]): number {
  if (nums.length === 0) return 0;
  return sumArray(nums) / nums.length;
}""",
    "after_code": """// math-utils.ts
export function sumArray(nums: number[]): number {
  return nums.reduce((acc, n) => acc + n);
}

export function average(nums: number[]): number {
  if (nums.length === 0) return 0;
  return sumArray(nums) / nums.length;
}""",
    "diff_summary": "sumArray reduce() lost its initialValue argument (0)",
    "ground_truth": {
      "will_break": ["sumArray([]) now throws 'Reduce of empty array with no initial value' — average([]) guard doesn't help because it calls sumArray after the guard"],
      "edge_cases": ["Single-element array [5] returns 5 correctly, masking the bug in most tests"],
      "broken_pattern": "reduce() without initialValue is fragile — rest of codebase uses initialValue consistently",
      "next_prompt": "Getting an unhandled error when computing statistics on empty datasets",
      "verified_by": "injected_bug",
      "notes": "Removing initialValue from reduce is a subtle empty-array trap"
    },
    "token_cost_manual_followup": 0
  },
  {
    "description": "getUserById swapped optional and required param",
    "before_code": """// user-service.ts
export async function getUserById(id: string, includeDeleted?: boolean): Promise<User | null> {
  const filter = includeDeleted ? {} : { deletedAt: null };
  return db.users.findOne({ id, ...filter });
}""",
    "after_code": """// user-service.ts
export async function getUserById(includeDeleted?: boolean, id?: string): Promise<User | null> {
  const filter = includeDeleted ? {} : { deletedAt: null };
  return db.users.findOne({ id, ...filter });
}""",
    "diff_summary": "getUserById parameter order swapped: id moved to second optional position, includeDeleted moved first",
    "ground_truth": {
      "will_break": ["All call sites getUserById(userId) now pass userId as includeDeleted (boolean coercion); id is undefined; all lookups return null"],
      "edge_cases": ["getUserById('admin-123') coerces string to truthy — includeDeleted=true, id=undefined; admin checks broken"],
      "broken_pattern": "Required parameter made optional and moved after optional — violates TypeScript convention; all existing callers silently broken",
      "next_prompt": "User lookups are all returning null / 404s everywhere",
      "verified_by": "injected_bug",
      "notes": "Swapped param order — no TS error at definition, errors manifest at call sites"
    },
    "token_cost_manual_followup": 0
  },
  {
    "description": "toggleFeatureFlag uses OR instead of XOR",
    "before_code": """// feature-flags.ts
export function toggleFeatureFlag(flags: Record<string, boolean>, key: string): Record<string, boolean> {
  return { ...flags, [key]: !flags[key] };
}""",
    "after_code": """// feature-flags.ts
export function toggleFeatureFlag(flags: Record<string, boolean>, key: string): Record<string, boolean> {
  return { ...flags, [key]: flags[key] || true };
}""",
    "diff_summary": "toggleFeatureFlag changed from !flags[key] to flags[key] || true",
    "ground_truth": {
      "will_break": ["Flags can never be turned off — flags[key] || true always evaluates to true; toggle is now a 'set to true' operation"],
      "edge_cases": ["Undefined/missing key: undefined || true = true — new flags created as enabled instead of toggled"],
      "broken_pattern": "Toggle semantics replaced with forced-enable; any UI that calls toggleFeatureFlag to disable a flag is now broken",
      "next_prompt": "I can't disable feature flags — toggling doesn't turn them off",
      "verified_by": "injected_bug",
      "notes": "|| true is a common accidental pattern when debugging"
    },
    "token_cost_manual_followup": 0
  },
  {
    "description": "sortByDate mutates original array",
    "before_code": """// list-utils.ts
export function sortByDate(items: { createdAt: string }[]): { createdAt: string }[] {
  return [...items].sort((a, b) => new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime());
}""",
    "after_code": """// list-utils.ts
export function sortByDate(items: { createdAt: string }[]): { createdAt: string }[] {
  return items.sort((a, b) => new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime());
}""",
    "diff_summary": "sortByDate removed spread copy [...items], now mutates the input array directly",
    "ground_truth": {
      "will_break": ["Callers that reuse the original array after sorting get it in sorted order unexpectedly — React state updates with stale sorted array cause render bugs"],
      "edge_cases": ["Store/redux state arrays mutated in place — immutability invariant violated, change detection breaks"],
      "broken_pattern": "Removed defensive copy; rest of list-utils functions use spread to avoid mutation",
      "next_prompt": "The list order is getting corrupted after sorting — other views showing sorted instead of original order",
      "verified_by": "injected_bug",
      "notes": "Classic mutation vs. immutability bug — easy to miss, hard to debug"
    },
    "token_cost_manual_followup": 0
  },
  {
    "description": "authenticate compares passwords with == instead of bcrypt",
    "before_code": """// auth.ts
import bcrypt from 'bcrypt';

export async function authenticate(inputPassword: string, hashedPassword: string): Promise<boolean> {
  return bcrypt.compare(inputPassword, hashedPassword);
}""",
    "after_code": """// auth.ts
export async function authenticate(inputPassword: string, hashedPassword: string): Promise<boolean> {
  return inputPassword == hashedPassword;
}""",
    "diff_summary": "authenticate replaced bcrypt.compare with loose equality comparison",
    "ground_truth": {
      "will_break": ["All login attempts fail — hashed passwords never equal plaintext; users locked out"],
      "edge_cases": ["If hashedPassword is somehow plain text (test/seed data), login works — masking the bug in dev environments"],
      "broken_pattern": "Removed cryptographic comparison; security regression — plaintext comparison exposes timing attack surface and bypasses hashing entirely",
      "next_prompt": "No one can log in — authentication is broken for all users",
      "verified_by": "injected_bug",
      "notes": "Critical security regression injected deliberately"
    },
    "token_cost_manual_followup": 0
  },
  {
    "description": "paginate returns wrong slice indices",
    "before_code": """// pagination.ts
export function paginate<T>(items: T[], page: number, pageSize: number): T[] {
  const start = (page - 1) * pageSize;
  return items.slice(start, start + pageSize);
}""",
    "after_code": """// pagination.ts
export function paginate<T>(items: T[], page: number, pageSize: number): T[] {
  const start = page * pageSize;
  return items.slice(start, start + pageSize);
}""",
    "diff_summary": "paginate changed start index from (page-1)*pageSize to page*pageSize",
    "ground_truth": {
      "will_break": ["Page 1 now returns items 10-19 instead of 0-9; first page is skipped entirely; last page returns empty array"],
      "edge_cases": ["page=0 now returns first page (previously would skip), changing behavior for callers that pass 0-indexed pages"],
      "broken_pattern": "Pagination changed from 1-indexed to 0-indexed without updating callers",
      "next_prompt": "The first page of results is missing — the list starts from item 11",
      "verified_by": "injected_bug",
      "notes": "Off-by-one in pagination index"
    },
    "token_cost_manual_followup": 0
  },
  {
    "description": "clamp function min/max parameters swapped in body",
    "before_code": """// math.ts
export function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}""",
    "after_code": """// math.ts
export function clamp(value: number, min: number, max: number): number {
  return Math.max(Math.min(value, min), max);
}""",
    "diff_summary": "clamp swapped Math.min and Math.max order — now returns max when value is below min",
    "ground_truth": {
      "will_break": ["clamp(5, 0, 10) returns 10 instead of 5 — all values clamped to max; UI sliders, progress bars, volume controls broken"],
      "edge_cases": ["clamp(0, 0, 10) returns 10 — even boundary values are wrong"],
      "broken_pattern": "Inverted min/max logic; function now always returns max for any input below max",
      "next_prompt": "Sliders are jumping to max value — clamping isn't working correctly",
      "verified_by": "injected_bug",
      "notes": "Swapped Math.min/Math.max nesting — subtle but breaks everything"
    },
    "token_cost_manual_followup": 0
  },
],
"B": [
  {
    "description": "Added fetchUserProfile async function without error handling",
    "before_code": """// api-client.ts
const BASE_URL = process.env.API_BASE_URL;

export async function fetchPosts(userId: string): Promise<Post[]> {
  const res = await fetch(`${BASE_URL}/users/${userId}/posts`);
  if (!res.ok) throw new Error(`Failed to fetch posts: ${res.status}`);
  return res.json();
}""",
    "after_code": """// api-client.ts
const BASE_URL = process.env.API_BASE_URL;

export async function fetchPosts(userId: string): Promise<Post[]> {
  const res = await fetch(`${BASE_URL}/users/${userId}/posts`);
  if (!res.ok) throw new Error(`Failed to fetch posts: ${res.status}`);
  return res.json();
}

export async function fetchUserProfile(userId: string): Promise<UserProfile> {
  const res = await fetch(`${BASE_URL}/users/${userId}/profile`);
  return res.json();
}""",
    "diff_summary": "Added fetchUserProfile async function that fetches user profile but has no error handling for non-OK responses",
    "ground_truth": {
      "will_break": [],
      "edge_cases": ["Non-OK HTTP response (404, 500) calls .json() on error body — may throw or return error payload typed as UserProfile; callers won't see the HTTP status"],
      "broken_pattern": "fetchUserProfile skips the res.ok check that fetchPosts has — inconsistent error handling pattern in same file",
      "next_prompt": "Profile page crashes on 404 users instead of showing a not-found state",
      "verified_by": "git_analogy",
      "notes": "Newly added function missing the established error-handling pattern"
    },
    "token_cost_manual_followup": 0
  },
  {
    "description": "Added exportToCsv async function with hardcoded delimiter",
    "before_code": """// export-utils.ts
export async function exportToJson(data: Record<string, unknown>[], filename: string): Promise<void> {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}""",
    "after_code": """// export-utils.ts
export async function exportToJson(data: Record<string, unknown>[], filename: string): Promise<void> {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export async function exportToCsv(data: Record<string, unknown>[], filename: string): Promise<void> {
  const headers = Object.keys(data[0]).join(',');
  const rows = data.map(row => Object.values(row).join(','));
  const csv = [headers, ...rows].join('\\n');
  const blob = new Blob([csv], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}""",
    "diff_summary": "Added exportToCsv that converts data array to CSV and triggers download",
    "ground_truth": {
      "will_break": [],
      "edge_cases": ["data[0] throws if data is empty array; values containing commas or newlines will corrupt the CSV (no quoting/escaping)"],
      "broken_pattern": "Hardcoded comma delimiter — international users may need semicolon; no handling of special characters in values unlike the careful JSON formatting in exportToJson",
      "next_prompt": "CSV export is corrupting rows that contain commas in the data",
      "verified_by": "git_analogy",
      "notes": "Common naive CSV generation without proper escaping"
    },
    "token_cost_manual_followup": 0
  },
  {
    "description": "Added sendWelcomeEmail that fires on every profile update",
    "before_code": """// user-service.ts
export async function updateUserProfile(userId: string, data: Partial<UserProfile>): Promise<UserProfile> {
  const updated = await db.users.update({ id: userId }, data);
  return updated;
}""",
    "after_code": """// user-service.ts
import { sendWelcomeEmail } from './email-service';

export async function updateUserProfile(userId: string, data: Partial<UserProfile>): Promise<UserProfile> {
  const updated = await db.users.update({ id: userId }, data);
  await sendWelcomeEmail(updated.email, updated.name);
  return updated;
}""",
    "diff_summary": "updateUserProfile now sends a welcome email after every profile update",
    "ground_truth": {
      "will_break": [],
      "edge_cases": ["Users receive welcome email every time they update their profile — spam regression; email sending failure now breaks profile updates (not isolated)"],
      "broken_pattern": "Welcome email logic belongs in the signup/onboarding flow, not in updateUserProfile; side effect added to a generic update function",
      "next_prompt": "Users are getting welcome emails every time they save their profile settings",
      "verified_by": "git_analogy",
      "notes": "Logic placed in wrong layer — welcome email should only fire on account creation"
    },
    "token_cost_manual_followup": 0
  },
  {
    "description": "Added cacheResult wrapper without cache invalidation",
    "before_code": """// product-service.ts
export async function getProduct(id: string): Promise<Product> {
  return db.products.findOne({ id });
}""",
    "after_code": """// product-service.ts
const cache = new Map<string, Product>();

export async function getProduct(id: string): Promise<Product> {
  if (cache.has(id)) return cache.get(id)!;
  const product = await db.products.findOne({ id });
  cache.set(id, product);
  return product;
}""",
    "diff_summary": "Added in-memory cache Map to getProduct with no TTL or invalidation",
    "ground_truth": {
      "will_break": [],
      "edge_cases": ["Product updates never reflected — cache serves stale data indefinitely; deleted products still returned from cache; cache grows unbounded in long-running process"],
      "broken_pattern": "Module-level mutable Map cache is a singleton — no invalidation, no TTL, no max size; rest of codebase uses Redis for caching with TTL",
      "next_prompt": "Product price changes aren't showing up — users are seeing old prices",
      "verified_by": "git_analogy",
      "notes": "Cache without invalidation is worse than no cache for correctness"
    },
    "token_cost_manual_followup": 0
  },
  {
    "description": "Added retryRequest but retries on 4xx errors too",
    "before_code": """// http-client.ts
export async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, options);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}""",
    "after_code": """// http-client.ts
export async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, options);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function retryRequest<T>(url: string, options?: RequestInit, retries = 3): Promise<T> {
  for (let i = 0; i < retries; i++) {
    try {
      return await request<T>(url, options);
    } catch (e) {
      if (i === retries - 1) throw e;
      await new Promise(r => setTimeout(r, 1000 * (i + 1)));
    }
  }
  throw new Error('Max retries exceeded');
}""",
    "diff_summary": "Added retryRequest function that retries any failed request up to 3 times with exponential backoff",
    "ground_truth": {
      "will_break": [],
      "edge_cases": ["Retries 401/403/404 responses — 3x the backend load for auth failures; retrying a POST may cause duplicate mutations (non-idempotent)"],
      "broken_pattern": "Should only retry 5xx (server errors) and network failures, not 4xx (client errors); no check for non-idempotent methods (POST/PATCH)",
      "next_prompt": "Login failures are taking 7 seconds instead of responding immediately",
      "verified_by": "git_analogy",
      "notes": "Retry-all is a common mistake — 4xx retries waste time and can cause duplicates"
    },
    "token_cost_manual_followup": 0
  },
  {
    "description": "Added useDebounce hook with missing cleanup",
    "before_code": """// hooks.ts
import { useState, useEffect } from 'react';

export function useLocalStorage<T>(key: string, initialValue: T) {
  const [value, setValue] = useState<T>(() => {
    const stored = localStorage.getItem(key);
    return stored ? JSON.parse(stored) : initialValue;
  });
  useEffect(() => { localStorage.setItem(key, JSON.stringify(value)); }, [key, value]);
  return [value, setValue] as const;
}""",
    "after_code": """// hooks.ts
import { useState, useEffect, useRef } from 'react';

export function useLocalStorage<T>(key: string, initialValue: T) {
  const [value, setValue] = useState<T>(() => {
    const stored = localStorage.getItem(key);
    return stored ? JSON.parse(stored) : initialValue;
  });
  useEffect(() => { localStorage.setItem(key, JSON.stringify(value)); }, [key, value]);
  return [value, setValue] as const;
}

export function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedValue(value), delay);
  }, [value, delay]);
  return debouncedValue;
}""",
    "diff_summary": "Added useDebounce hook that delays value updates using setTimeout",
    "ground_truth": {
      "will_break": [],
      "edge_cases": ["Timer not cleared on unmount or value change — state update after unmount causes React memory leak warning; rapid input changes stack up timers"],
      "broken_pattern": "useEffect missing return () => clearTimeout(timer) — useLocalStorage in same file correctly uses no timer but the pattern for cleanup is established in React docs",
      "next_prompt": "Getting 'Can't perform a React state update on an unmounted component' warning in console",
      "verified_by": "git_analogy",
      "notes": "Missing cleanup in useEffect is one of the most common React hooks mistakes"
    },
    "token_cost_manual_followup": 0
  },
  {
    "description": "Added uploadFile that doesn't validate file type or size",
    "before_code": """// file-service.ts
export async function deleteFile(fileId: string, userId: string): Promise<void> {
  const file = await db.files.findOne({ id: fileId });
  if (file.ownerId !== userId) throw new Error('Unauthorized');
  await storage.delete(file.storageKey);
  await db.files.delete({ id: fileId });
}""",
    "after_code": """// file-service.ts
export async function deleteFile(fileId: string, userId: string): Promise<void> {
  const file = await db.files.findOne({ id: fileId });
  if (file.ownerId !== userId) throw new Error('Unauthorized');
  await storage.delete(file.storageKey);
  await db.files.delete({ id: fileId });
}

export async function uploadFile(file: File, userId: string): Promise<string> {
  const key = `users/${userId}/${Date.now()}-${file.name}`;
  await storage.put(key, file);
  await db.files.create({ ownerId: userId, storageKey: key, name: file.name });
  return key;
}""",
    "diff_summary": "Added uploadFile function that stores files to cloud storage without type or size validation",
    "ground_truth": {
      "will_break": [],
      "edge_cases": ["No file size limit — users can upload arbitrarily large files; no MIME type check — executable files (.exe, .sh, .php) can be uploaded and served"],
      "broken_pattern": "deleteFile has authorization check; uploadFile has none — only checks userId is provided, not that it's the authenticated user; no rate limiting",
      "next_prompt": "Can we add a file size limit and restrict to image/document types?",
      "verified_by": "git_analogy",
      "notes": "Upload endpoint without validation is a common security gap"
    },
    "token_cost_manual_followup": 0
  },
  {
    "description": "Added generateReport that blocks the event loop",
    "before_code": """// report-service.ts
export async function getReportMetadata(reportId: string): Promise<ReportMeta> {
  return db.reports.findOne({ id: reportId });
}""",
    "after_code": """// report-service.ts
export async function getReportMetadata(reportId: string): Promise<ReportMeta> {
  return db.reports.findOne({ id: reportId });
}

export async function generateReport(data: ReportRow[]): Promise<string> {
  let csv = 'id,name,value,date\\n';
  for (const row of data) {
    // Heavy synchronous processing
    const processed = JSON.stringify(row).repeat(1);
    csv += `${row.id},${row.name},${row.value},${row.date}\\n`;
  }
  return csv;
}""",
    "diff_summary": "Added generateReport that synchronously builds a CSV string for potentially large datasets",
    "ground_truth": {
      "will_break": [],
      "edge_cases": ["Large datasets (10k+ rows) block Node.js event loop for hundreds of ms; no streaming — entire CSV built in memory before returning"],
      "broken_pattern": "Synchronous loop in an async function — function is async but does no actual async work; should use streams or worker threads for large data",
      "next_prompt": "The API is timing out when generating reports with large datasets",
      "verified_by": "git_analogy",
      "notes": "CPU-bound work in async function is a common Node.js anti-pattern"
    },
    "token_cost_manual_followup": 0
  },
  {
    "description": "Added useInfiniteScroll hook that fires on every scroll event",
    "before_code": """// scroll-hooks.ts
import { useEffect, useRef } from 'react';

export function useScrollToTop(smooth = true) {
  return () => window.scrollTo({ top: 0, behavior: smooth ? 'smooth' : 'auto' });
}""",
    "after_code": """// scroll-hooks.ts
import { useEffect, useRef, useState } from 'react';

export function useScrollToTop(smooth = true) {
  return () => window.scrollTo({ top: 0, behavior: smooth ? 'smooth' : 'auto' });
}

export function useInfiniteScroll(onLoadMore: () => void, threshold = 200) {
  useEffect(() => {
    const handleScroll = () => {
      const nearBottom = window.innerHeight + window.scrollY >= document.body.offsetHeight - threshold;
      if (nearBottom) onLoadMore();
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, [onLoadMore, threshold]);
}""",
    "diff_summary": "Added useInfiniteScroll hook that calls onLoadMore when user scrolls near bottom",
    "ground_truth": {
      "will_break": [],
      "edge_cases": ["onLoadMore fires repeatedly on every scroll event when near bottom — floods API with requests; no loading state guard or debounce"],
      "broken_pattern": "No throttle/debounce on scroll handler — fires at 60fps; no isLoading check to prevent concurrent load-more calls; threshold check is one-shot but re-fires continuously",
      "next_prompt": "Infinite scroll is making hundreds of API requests when I scroll to the bottom",
      "verified_by": "git_analogy",
      "notes": "Scroll handler without throttle is a classic performance/correctness bug"
    },
    "token_cost_manual_followup": 0
  },
  {
    "description": "Added refreshToken that doesn't handle concurrent refresh calls",
    "before_code": """// auth-service.ts
export async function getAccessToken(): Promise<string> {
  const token = localStorage.getItem('access_token');
  if (!token) throw new Error('Not authenticated');
  return token;
}""",
    "after_code": """// auth-service.ts
export async function getAccessToken(): Promise<string> {
  const token = localStorage.getItem('access_token');
  if (!token) throw new Error('Not authenticated');
  return token;
}

export async function refreshToken(): Promise<string> {
  const refresh = localStorage.getItem('refresh_token');
  const res = await fetch('/api/auth/refresh', {
    method: 'POST',
    body: JSON.stringify({ refresh_token: refresh }),
    headers: { 'Content-Type': 'application/json' }
  });
  const { access_token } = await res.json();
  localStorage.setItem('access_token', access_token);
  return access_token;
}""",
    "diff_summary": "Added refreshToken function that exchanges refresh token for new access token",
    "ground_truth": {
      "will_break": [],
      "edge_cases": ["Concurrent requests all calling refreshToken simultaneously send multiple refresh requests — race condition can invalidate tokens; no singleton promise guard"],
      "broken_pattern": "No check for res.ok — failed refresh returns undefined access_token stored as 'undefined' string; no clearing of invalid refresh token on 401",
      "next_prompt": "After token expiry, multiple simultaneous requests cause a 401 storm",
      "verified_by": "git_analogy",
      "notes": "Token refresh without mutex/singleton is a well-known race condition"
    },
    "token_cost_manual_followup": 0
  },
  {
    "description": "Added filterByPermission that uses client-side role check",
    "before_code": """// data-service.ts
export async function getDocuments(orgId: string): Promise<Document[]> {
  return db.documents.find({ orgId });
}""",
    "after_code": """// data-service.ts
export async function getDocuments(orgId: string): Promise<Document[]> {
  return db.documents.find({ orgId });
}

export function filterByPermission(docs: Document[], userRole: string): Document[] {
  if (userRole === 'admin') return docs;
  return docs.filter(doc => doc.visibility === 'public');
}""",
    "diff_summary": "Added filterByPermission function that filters documents client-side based on user role",
    "ground_truth": {
      "will_break": [],
      "edge_cases": ["getDocuments still returns all documents including private ones — filtering happens after full data is fetched; malicious client can bypass filter"],
      "broken_pattern": "Permission filtering should happen in the database query (server-side), not after fetching all data; role string comparison is fragile (case sensitivity, typos)",
      "next_prompt": "Can we move the permission check to the database query so we don't over-fetch?",
      "verified_by": "git_analogy",
      "notes": "Client-side security filtering is a security anti-pattern"
    },
    "token_cost_manual_followup": 0
  },
  {
    "description": "Added sendNotification with no rate limiting",
    "before_code": """// notification-service.ts
export async function getNotificationPrefs(userId: string): Promise<NotificationPrefs> {
  return db.notificationPrefs.findOne({ userId });
}""",
    "after_code": """// notification-service.ts
export async function getNotificationPrefs(userId: string): Promise<NotificationPrefs> {
  return db.notificationPrefs.findOne({ userId });
}

export async function sendNotification(userId: string, message: string, channel: 'email' | 'sms' | 'push'): Promise<void> {
  const prefs = await getNotificationPrefs(userId);
  if (!prefs[channel]) return;
  await notificationProvider.send({ userId, message, channel });
  await db.notifications.create({ userId, message, channel, sentAt: new Date() });
}""",
    "diff_summary": "Added sendNotification that respects user preferences and sends via specified channel",
    "ground_truth": {
      "will_break": [],
      "edge_cases": ["No rate limiting — a bug or loop in calling code could spam users with thousands of notifications; no deduplication of identical messages sent close together"],
      "broken_pattern": "No idempotency key or deduplication check; notification logging happens after send — if send succeeds but db.create fails, no audit trail",
      "next_prompt": "Can you add rate limiting so users don't get flooded with notifications?",
      "verified_by": "git_analogy",
      "notes": "Notification services need rate limiting as a baseline"
    },
    "token_cost_manual_followup": 0
  },
],
"C": [
  {
    "description": "Extract validate_email utility but forget to handle edge cases from original",
    "before_code": """# user_service.py
import re

def create_user(email: str, username: str) -> dict:
    if not email or '@' not in email:
        raise ValueError("Invalid email")
    if len(email) > 254:
        raise ValueError("Email too long")
    if '..' in email:
        raise ValueError("Invalid email format")
    # ... create user logic
    return {"email": email, "username": username}

def update_email(user_id: str, new_email: str) -> dict:
    if not new_email or '@' not in new_email:
        raise ValueError("Invalid email")
    if len(new_email) > 254:
        raise ValueError("Email too long")
    # ... update logic
    return {"id": user_id, "email": new_email}""",
    "after_code": """# user_service.py
import re
from utils import validate_email

def create_user(email: str, username: str) -> dict:
    validate_email(email)
    return {"email": email, "username": username}

def update_email(user_id: str, new_email: str) -> dict:
    validate_email(new_email)
    return {"id": user_id, "email": new_email}

# utils.py
def validate_email(email: str) -> None:
    if not email or '@' not in email:
        raise ValueError("Invalid email")
    if len(email) > 254:
        raise ValueError("Email too long")""",
    "diff_summary": "Extracted email validation into validate_email utility in utils.py, but '..' check not carried over",
    "ground_truth": {
      "will_break": [],
      "edge_cases": ["Emails with consecutive dots (e.g. 'user..name@example.com') now pass validation in create_user — the '..' check was in original but lost during extraction"],
      "broken_pattern": "update_email had fewer checks than create_user originally — the refactor made them consistent but at the lower bar; lost a validation rule silently",
      "next_prompt": "Can you add the double-dot check back to the email validator?",
      "verified_by": "git_analogy",
      "notes": "Refactoring often loses edge case handling — classic extraction bug"
    },
    "token_cost_manual_followup": 0
  },
  {
    "description": "Extract format_price utility changes rounding behavior",
    "before_code": """# cart.py
def calculate_total(items: list) -> str:
    total = sum(item['price'] * item['qty'] for item in items)
    return f"${total:.2f}"

# invoice.py
def get_invoice_total(line_items: list) -> str:
    total = sum(item['amount'] for item in line_items)
    return f"${round(total, 2):.2f}" """,
    "after_code": """# price_utils.py
import math

def format_price(amount: float) -> str:
    return f"${math.ceil(amount * 100) / 100:.2f}"

# cart.py
from price_utils import format_price

def calculate_total(items: list) -> str:
    total = sum(item['price'] * item['qty'] for item in items)
    return format_price(total)

# invoice.py
from price_utils import format_price

def get_invoice_total(line_items: list) -> str:
    total = sum(item['amount'] for item in line_items)
    return format_price(total)""",
    "diff_summary": "Extracted format_price utility but uses math.ceil rounding instead of standard round()",
    "ground_truth": {
      "will_break": [],
      "edge_cases": ["math.ceil rounds up — $1.001 shows as $1.01 instead of $1.00; floating point totals like 10.005 now ceil to 10.01 instead of rounding to 10.00"],
      "broken_pattern": "cart.py used :.2f (banker's rounding), invoice.py used round() — both replaced with ceil() which overcharges customers by rounding up",
      "next_prompt": "Customer is complaining the invoice total is a penny higher than the cart total",
      "verified_by": "git_analogy",
      "notes": "Rounding behavior changed silently during extraction — financial logic needs exact rounding"
    },
    "token_cost_manual_followup": 0
  },
  {
    "description": "Extract get_db_connection into shared utility breaks connection pooling",
    "before_code": """# users.py
import psycopg2

def get_user(user_id: str):
    conn = psycopg2.connect(dsn=os.environ['DATABASE_URL'])
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result

# posts.py
import psycopg2

def get_post(post_id: str):
    conn = psycopg2.connect(dsn=os.environ['DATABASE_URL'])
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM posts WHERE id = %s", (post_id,))
    result = cursor.fetchone()
    conn.close()
    return result""",
    "after_code": """# db.py
import psycopg2

_conn = None

def get_db_connection():
    global _conn
    if _conn is None:
        _conn = psycopg2.connect(dsn=os.environ['DATABASE_URL'])
    return _conn

# users.py
from db import get_db_connection

def get_user(user_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    return cursor.fetchone()

# posts.py
from db import get_db_connection

def get_post(post_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM posts WHERE id = %s", (post_id,))
    return cursor.fetchone()""",
    "diff_summary": "Extracted database connection into singleton get_db_connection in db.py to avoid duplication",
    "ground_truth": {
      "will_break": [],
      "edge_cases": ["Singleton connection is not thread-safe — concurrent requests share one connection; if connection drops, _conn stays set to closed connection; no reconnection logic"],
      "broken_pattern": "Original code opened and closed connections per-request (correct for high concurrency); new singleton reuses one connection (wrong — should use a connection pool like psycopg2.pool)",
      "next_prompt": "Getting 'connection is closed' errors under load",
      "verified_by": "git_analogy",
      "notes": "Singleton DB connection is a common refactoring mistake — breaks thread safety"
    },
    "token_cost_manual_followup": 0
  },
  {
    "description": "Extract send_email utility strips template variable handling",
    "before_code": """# welcome.py
import smtplib

def send_welcome_email(user_email: str, username: str):
    body = f"Welcome, {username}! Thanks for joining."
    msg = f"Subject: Welcome\\nTo: {user_email}\\n\\n{body}"
    with smtplib.SMTP('localhost') as s:
        s.sendmail('noreply@app.com', user_email, msg)

# reset.py
def send_reset_email(user_email: str, reset_link: str):
    body = f"Reset your password: {reset_link}"
    msg = f"Subject: Password Reset\\nTo: {user_email}\\n\\n{body}"
    with smtplib.SMTP('localhost') as s:
        s.sendmail('noreply@app.com', user_email, msg)""",
    "after_code": """# email_utils.py
import smtplib

def send_email(to: str, subject: str, body: str):
    msg = f"Subject: {subject}\\nTo: {to}\\n\\n{body}"
    with smtplib.SMTP('localhost') as s:
        s.sendmail('noreply@app.com', to, msg)

# welcome.py
from email_utils import send_email

def send_welcome_email(user_email: str, username: str):
    send_email(user_email, "Welcome", "Welcome! Thanks for joining.")

# reset.py
from email_utils import send_email

def send_reset_email(user_email: str, reset_link: str):
    send_email(user_email, "Password Reset", "Reset your password: " + reset_link)""",
    "diff_summary": "Extracted send_email utility but welcome email no longer includes the username in the greeting",
    "ground_truth": {
      "will_break": [],
      "edge_cases": ["send_reset_email concatenates reset_link directly — if link contains special SMTP chars or newline injection, header injection possible"],
      "broken_pattern": "welcome email lost username personalization during extraction — the template variable {username} was dropped without noticing",
      "next_prompt": "Welcome emails are no longer showing the user's name",
      "verified_by": "git_analogy",
      "notes": "Personalization lost during refactor — easy to miss when body is hardcoded"
    },
    "token_cost_manual_followup": 0
  },
  {
    "description": "Extract normalize_phone drops country code handling",
    "before_code": """# checkout.py
import re

def process_checkout(phone: str, amount: float):
    cleaned = re.sub(r'[^\\d+]', '', phone)
    if cleaned.startswith('+'):
        cleaned = cleaned  # keep country code
    elif len(cleaned) == 10:
        cleaned = '+1' + cleaned  # assume US
    # ... process payment
    return {"phone": cleaned, "amount": amount}

# profile.py
def save_phone(user_id: str, phone: str):
    cleaned = re.sub(r'[^\\d]', '', phone)  # strips + too
    if len(cleaned) == 10:
        cleaned = '1' + cleaned
    # ... save to db""",
    "after_code": """# phone_utils.py
import re

def normalize_phone(phone: str) -> str:
    return re.sub(r'[^\\d]', '', phone)

# checkout.py
from phone_utils import normalize_phone

def process_checkout(phone: str, amount: float):
    cleaned = normalize_phone(phone)
    return {"phone": cleaned, "amount": amount}

# profile.py
from phone_utils import normalize_phone

def save_phone(user_id: str, phone: str):
    cleaned = normalize_phone(phone)
    # ... save to db""",
    "diff_summary": "Extracted normalize_phone utility but it strips the + prefix and drops country code defaulting logic",
    "ground_truth": {
      "will_break": [],
      "edge_cases": ["International numbers with + stripped — '+447911123456' becomes '447911123456'; checkout no longer defaults 10-digit numbers to US +1"],
      "broken_pattern": "checkout.py had the better implementation (kept + prefix, defaulted to +1); profile.py had the weaker one; refactor standardized on the weaker version",
      "next_prompt": "International phone numbers are being stored without the country code",
      "verified_by": "git_analogy",
      "notes": "Refactor unified to the wrong (weaker) implementation"
    },
    "token_cost_manual_followup": 0
  },
  {
    "description": "Extract parse_config breaks environment-specific overrides",
    "before_code": """# app.py
import os, json

def load_config():
    with open('config.json') as f:
        config = json.load(f)
    # Environment overrides
    if os.environ.get('DEBUG'):
        config['debug'] = True
    if os.environ.get('DB_URL'):
        config['database']['url'] = os.environ['DB_URL']
    return config""",
    "after_code": """# config_utils.py
import json

def parse_config(path: str = 'config.json') -> dict:
    with open(path) as f:
        return json.load(f)

# app.py
from config_utils import parse_config

def load_config():
    return parse_config()""",
    "diff_summary": "Extracted config parsing into parse_config utility, but env var override logic was not carried over",
    "ground_truth": {
      "will_break": ["DB_URL environment variable no longer overrides database config — production deployments that set DB_URL will use config.json value instead, likely pointing to dev DB"],
      "edge_cases": ["DEBUG env var no longer enables debug mode — production debug flag now controlled only by config.json, not deployment environment"],
      "broken_pattern": "Config loading should merge file + environment; extracted utility handles only file loading; 12-factor app pattern (env vars override config) broken",
      "next_prompt": "Production is connecting to the wrong database — DB_URL env var is being ignored",
      "verified_by": "git_analogy",
      "notes": "Env var overrides are critical in production and easily lost during refactoring"
    },
    "token_cost_manual_followup": 0
  },
  {
    "description": "Extract log_event utility changes log level semantics",
    "before_code": """# payment.py
import logging
logger = logging.getLogger(__name__)

def process_payment(amount: float, card_token: str):
    logger.info(f"Processing payment amount={amount}")
    if amount <= 0:
        logger.error(f"Invalid payment amount: {amount}")
        raise ValueError("Invalid amount")
    logger.info(f"Payment processed successfully amount={amount}")

# auth.py
def login_attempt(user_id: str, success: bool):
    if success:
        logging.getLogger(__name__).info(f"Login success user={user_id}")
    else:
        logging.getLogger(__name__).warning(f"Login failed user={user_id}")""",
    "after_code": """# log_utils.py
import logging

def log_event(event: str, data: dict, level: str = 'info'):
    logging.getLogger('app').info(f"{event}: {data}")

# payment.py
from log_utils import log_event

def process_payment(amount: float, card_token: str):
    log_event("payment.start", {"amount": amount})
    if amount <= 0:
        log_event("payment.invalid", {"amount": amount}, level='error')
        raise ValueError("Invalid amount")
    log_event("payment.success", {"amount": amount})

# auth.py
from log_utils import log_event

def login_attempt(user_id: str, success: bool):
    level = 'info' if success else 'warning'
    log_event("login", {"user": user_id, "success": success}, level=level)""",
    "diff_summary": "Extracted log_event utility with a level parameter, but the implementation ignores the level and always calls logging.info",
    "ground_truth": {
      "will_break": [],
      "edge_cases": ["Error and warning events now logged as INFO — alerting systems watching for ERROR/WARNING log levels won't trigger; failed logins silently downgraded to info"],
      "broken_pattern": "level parameter accepted but ignored in implementation — interface promises level control but doesn't deliver it",
      "next_prompt": "Our error alerting stopped firing — payment errors aren't showing as errors in the logs",
      "verified_by": "git_analogy",
      "notes": "Parameter accepted but not used — silent contract violation"
    },
    "token_cost_manual_followup": 0
  },
  {
    "description": "Extract paginate_query loses total count for pagination UI",
    "before_code": """# api/users.py
def list_users(page: int, page_size: int = 20) -> dict:
    offset = (page - 1) * page_size
    users = db.execute("SELECT * FROM users LIMIT %s OFFSET %s", (page_size, offset))
    total = db.execute("SELECT COUNT(*) FROM users")[0][0]
    return {"items": users, "total": total, "page": page, "page_size": page_size}

# api/posts.py
def list_posts(page: int, page_size: int = 20) -> dict:
    offset = (page - 1) * page_size
    posts = db.execute("SELECT * FROM posts LIMIT %s OFFSET %s", (page_size, offset))
    total = db.execute("SELECT COUNT(*) FROM posts")[0][0]
    return {"items": posts, "total": total, "page": page, "page_size": page_size}""",
    "after_code": """# db_utils.py
def paginate_query(table: str, page: int, page_size: int = 20) -> list:
    offset = (page - 1) * page_size
    return db.execute(f"SELECT * FROM {table} LIMIT %s OFFSET %s", (page_size, offset))

# api/users.py
from db_utils import paginate_query

def list_users(page: int, page_size: int = 20) -> dict:
    users = paginate_query('users', page, page_size)
    return {"items": users, "page": page}

# api/posts.py
from db_utils import paginate_query

def list_posts(page: int, page_size: int = 20) -> dict:
    posts = paginate_query('posts', page, page_size)
    return {"items": posts, "page": page}""",
    "diff_summary": "Extracted paginate_query utility but total count query removed from both endpoints",
    "ground_truth": {
      "will_break": ["Frontend pagination UI that uses response.total to calculate page count now gets undefined — pagination controls broken"],
      "edge_cases": ["SQL injection via table name parameter — paginate_query('users; DROP TABLE users --', ...) would execute"],
      "broken_pattern": "Response shape changed — removed 'total' and 'page_size' from response without versioning the API; table name interpolated directly into SQL",
      "next_prompt": "The pagination controls have disappeared — the frontend can't calculate total pages",
      "verified_by": "git_analogy",
      "notes": "Refactor dropped functionality and introduced SQL injection"
    },
    "token_cost_manual_followup": 0
  },
  {
    "description": "Extract retry_on_failure decorator changes exception handling scope",
    "before_code": """# external_api.py
import time, requests

def call_weather_api(city: str) -> dict:
    for attempt in range(3):
        try:
            response = requests.get(f"https://api.weather.com/{city}", timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.Timeout:
            if attempt == 2: raise
            time.sleep(2 ** attempt)
        except requests.HTTPError as e:
            if e.response.status_code >= 500:
                if attempt == 2: raise
                time.sleep(2 ** attempt)
            else:
                raise  # don't retry 4xx""",
    "after_code": """# retry_utils.py
import time, functools

def retry_on_failure(max_attempts=3):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception:
                    if attempt == max_attempts - 1: raise
                    time.sleep(2 ** attempt)
        return wrapper
    return decorator

# external_api.py
import requests
from retry_utils import retry_on_failure

@retry_on_failure(max_attempts=3)
def call_weather_api(city: str) -> dict:
    response = requests.get(f"https://api.weather.com/{city}", timeout=5)
    response.raise_for_status()
    return response.json()""",
    "diff_summary": "Extracted retry logic into retry_on_failure decorator that catches all Exception types",
    "ground_truth": {
      "will_break": [],
      "edge_cases": ["Retries 404/401/400 responses (HTTPError for 4xx) — original code explicitly raised immediately on 4xx; now delays 4xx retries wasting 6 seconds before failing"],
      "broken_pattern": "Original retry was selective (Timeout + 5xx only); new decorator retries all Exception — over-broad exception catching is an anti-pattern; retrying 4xx is wrong",
      "next_prompt": "API calls to invalid cities are now taking 6 seconds to fail instead of immediately",
      "verified_by": "git_analogy",
      "notes": "catch Exception is too broad — lost selective retry logic"
    },
    "token_cost_manual_followup": 0
  },
  {
    "description": "Extract hash_password changes algorithm without migration",
    "before_code": """# user_auth.py
import hashlib

def hash_password(password: str, salt: str) -> str:
    return hashlib.sha256((password + salt).encode()).hexdigest()

def verify_password(password: str, salt: str, stored_hash: str) -> bool:
    return hash_password(password, salt) == stored_hash""",
    "after_code": """# crypto_utils.py
import bcrypt

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, stored_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), stored_hash.encode())

# user_auth.py
from crypto_utils import hash_password, verify_password""",
    "diff_summary": "Migrated password hashing from SHA-256 with salt to bcrypt in extracted utility",
    "ground_truth": {
      "will_break": ["verify_password now fails for all existing users — bcrypt.checkpw against SHA-256 hashes always returns False; all users locked out until passwords reset"],
      "edge_cases": ["No migration path — existing sha256 hashes in DB are incompatible with bcrypt verification; salt parameter removed breaks any callers passing salt"],
      "broken_pattern": "Algorithm change requires a migration strategy (e.g. detect hash type, verify old way and re-hash); dropped the salt parameter breaks existing call sites",
      "next_prompt": "All existing users can't log in after the deployment",
      "verified_by": "git_analogy",
      "notes": "Changing hash algorithm without migration is a user-locking bug"
    },
    "token_cost_manual_followup": 0
  },
  {
    "description": "Extract build_query utility introduces SQL injection via f-string",
    "before_code": """# search.py
import psycopg2

def search_products(name: str, category: str, max_price: float) -> list:
    query = "SELECT * FROM products WHERE 1=1"
    params = []
    if name:
        query += " AND name ILIKE %s"
        params.append(f"%{name}%")
    if category:
        query += " AND category = %s"
        params.append(category)
    if max_price:
        query += " AND price <= %s"
        params.append(max_price)
    return db.execute(query, params)""",
    "after_code": """# query_utils.py
def build_query(table: str, filters: dict) -> str:
    conditions = " AND ".join(f"{k} = '{v}'" for k, v in filters.items())
    return f"SELECT * FROM {table} WHERE {conditions}"

# search.py
from query_utils import build_query

def search_products(name: str, category: str, max_price: float) -> list:
    filters = {}
    if name: filters['name'] = name
    if category: filters['category'] = category
    if max_price: filters['price'] = max_price
    query = build_query('products', filters)
    return db.execute(query)""",
    "diff_summary": "Extracted query builder utility that uses f-strings to construct SQL from user inputs",
    "ground_truth": {
      "will_break": [],
      "edge_cases": ["Direct SQL injection via name/category/max_price — build_query interpolates values directly into SQL string; name=\"'; DROP TABLE products;--\" works"],
      "broken_pattern": "Original used parameterized queries (correct); replacement uses string interpolation (SQL injection vulnerability); ILIKE search (partial match) replaced with = (exact match) — search now broken",
      "next_prompt": "Product search is only finding exact name matches instead of partial matches",
      "verified_by": "git_analogy",
      "notes": "Introduced SQL injection while refactoring — parameterized queries replaced with string interpolation"
    },
    "token_cost_manual_followup": 0
  },
  {
    "description": "Extract serialize_user drops password hash from output but also drops required fields",
    "before_code": """# api/users.py
def get_user_response(user: dict) -> dict:
    return {
        "id": user["id"],
        "email": user["email"],
        "name": user["name"],
        "role": user["role"],
        "created_at": user["created_at"].isoformat(),
        # deliberately exclude: password_hash, reset_token, internal_flags
    }""",
    "after_code": """# serializers.py
SAFE_FIELDS = ['id', 'email', 'name']

def serialize_user(user: dict) -> dict:
    return {k: user[k] for k in SAFE_FIELDS if k in user}

# api/users.py
from serializers import serialize_user

def get_user_response(user: dict) -> dict:
    return serialize_user(user)""",
    "diff_summary": "Extracted serialize_user utility using a SAFE_FIELDS allowlist that excludes sensitive fields",
    "ground_truth": {
      "will_break": ["API responses missing role and created_at fields — frontend components that depend on user.role for permission checks will fail; role-based UI will break"],
      "edge_cases": ["created_at no longer .isoformat() — if frontend receives datetime object (non-serializable), JSON serialization throws"],
      "broken_pattern": "SAFE_FIELDS allowlist is more restrictive than original — omitted role and created_at which are needed by frontend; original explicitly commented which fields to exclude",
      "next_prompt": "The frontend is throwing errors about user.role being undefined",
      "verified_by": "git_analogy",
      "notes": "Over-aggressive field filtering broke required API contract fields"
    },
    "token_cost_manual_followup": 0
  },
],
"D": [
  {
    "description": "UserProfile type adds required field breaking all partial update callers",
    "before_code": """// types.ts
export interface UserProfile {
  id: string;
  displayName: string;
  bio?: string;
  avatarUrl?: string;
}

// profile-service.ts
export async function updateProfile(userId: string, updates: Partial<UserProfile>): Promise<UserProfile> {
  return db.profiles.update({ id: userId }, updates);
}

// profile-form.tsx
export function ProfileForm({ profile }: { profile: UserProfile }) {
  const [name, setName] = useState(profile.displayName);
  // ...
}""",
    "after_code": """// types.ts
export interface UserProfile {
  id: string;
  displayName: string;
  bio?: string;
  avatarUrl?: string;
  lastActiveAt: Date;  // new required field
}

// profile-service.ts
export async function updateProfile(userId: string, updates: Partial<UserProfile>): Promise<UserProfile> {
  return db.profiles.update({ id: userId }, updates);
}

// profile-form.tsx
export function ProfileForm({ profile }: { profile: UserProfile }) {
  const [name, setName] = useState(profile.displayName);
  // ...
}""",
    "diff_summary": "Added required lastActiveAt: Date field to UserProfile interface",
    "ground_truth": {
      "will_break": ["Any code constructing a full UserProfile object (not Partial) will get TS error for missing lastActiveAt; existing DB rows without this column will fail to deserialize at runtime"],
      "edge_cases": ["Date vs string: if DB returns ISO string, TypeScript type says Date — runtime type mismatch; JSON.parse gives string, not Date object"],
      "broken_pattern": "Adding a required field to an existing interface without a migration — should be optional (lastActiveAt?: Date) until all rows are backfilled",
      "next_prompt": "TypeScript errors everywhere saying 'Property lastActiveAt is missing in type'",
      "verified_by": "git_analogy",
      "notes": "Required field addition to interface is a breaking change requiring careful migration"
    },
    "token_cost_manual_followup": 0
  },
  {
    "description": "API response type discriminated union changes break switch exhaustiveness",
    "before_code": """// api-types.ts
export type ApiResponse<T> =
  | { status: 'success'; data: T }
  | { status: 'error'; message: string };

// handlers.ts
function handleResponse<T>(res: ApiResponse<T>): T {
  if (res.status === 'success') return res.data;
  throw new Error(res.message);
}""",
    "after_code": """// api-types.ts
export type ApiResponse<T> =
  | { status: 'success'; data: T }
  | { status: 'error'; message: string; code: number }
  | { status: 'pending'; requestId: string };  // new variant

// handlers.ts
function handleResponse<T>(res: ApiResponse<T>): T {
  if (res.status === 'success') return res.data;
  throw new Error(res.message);  // 'pending' has no message — TS error
}""",
    "diff_summary": "Added 'pending' variant to ApiResponse discriminated union without updating switch/if-else handlers",
    "ground_truth": {
      "will_break": ["handleResponse tries res.message on 'pending' type which has no message property — TS error; runtime: res.message is undefined, throws 'undefined' as error message"],
      "edge_cases": ["Any switch(res.status) without a 'pending' case — TypeScript exhaustiveness check fails or default branch handles pending incorrectly"],
      "broken_pattern": "Adding a discriminated union variant requires updating all exhaustive handlers; error variant now has code field that handlers ignore",
      "next_prompt": "TypeScript is complaining that 'pending' doesn't have a 'message' property",
      "verified_by": "git_analogy",
      "notes": "Discriminated union expansion is a well-known breaking change pattern"
    },
    "token_cost_manual_followup": 0
  },
  {
    "description": "Event payload type narrows string to literal union breaking existing emitters",
    "before_code": """// events.ts
export interface UserEvent {
  type: string;
  userId: string;
  timestamp: number;
  metadata?: Record<string, unknown>;
}

// emitter.ts
export function emitUserEvent(event: UserEvent): void {
  eventBus.emit('user', event);
}""",
    "after_code": """// events.ts
export type UserEventType = 'login' | 'logout' | 'profile_update' | 'password_change';

export interface UserEvent {
  type: UserEventType;
  userId: string;
  timestamp: number;
  metadata?: Record<string, unknown>;
}

// emitter.ts
export function emitUserEvent(event: UserEvent): void {
  eventBus.emit('user', event);
}""",
    "diff_summary": "Narrowed UserEvent.type from string to a UserEventType literal union",
    "ground_truth": {
      "will_break": ["Any caller emitting custom event types (e.g. 'email_verified', 'subscription_renewed') now gets TS error — they're not in the literal union"],
      "edge_cases": ["Runtime emitters using dynamic string event types (from external config, webhook payloads) will fail TS compilation even though runtime behavior is the same"],
      "broken_pattern": "Narrowing a public interface type from string to literal union is a breaking change for all emitters using custom event types; needs a major version bump or 'string &' escape hatch",
      "next_prompt": "TS errors on our custom event types — they're not in UserEventType",
      "verified_by": "git_analogy",
      "notes": "Type narrowing as a breaking change — common in schema evolution"
    },
    "token_cost_manual_followup": 0
  },
  {
    "description": "Database schema adds NOT NULL column without migration default",
    "before_code": """-- migration_003.sql
CREATE TABLE orders (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES users(id),
  total_cents INTEGER NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);""",
    "after_code": """-- migration_004.sql
ALTER TABLE orders ADD COLUMN shipping_address_id UUID NOT NULL REFERENCES addresses(id);""",
    "diff_summary": "Added NOT NULL shipping_address_id column to orders table without a default value",
    "ground_truth": {
      "will_break": ["Migration fails on existing rows — PostgreSQL cannot add NOT NULL column without DEFAULT to a non-empty table; 'ERROR: column contains null values'"],
      "edge_cases": ["Even if table is empty in prod, application code that creates orders without shipping_address_id will fail immediately after migration"],
      "broken_pattern": "NOT NULL addition requires: add as nullable, backfill data, then add NOT NULL constraint; or add with a DEFAULT — skipped the backfill/default step",
      "next_prompt": "The migration is failing in production with 'column contains null values'",
      "verified_by": "git_analogy",
      "notes": "Classic safe migration violation — adding NOT NULL without default breaks on live data"
    },
    "token_cost_manual_followup": 0
  },
  {
    "description": "GraphQL schema type field changes from nullable to non-null breaking clients",
    "before_code": """# schema.graphql
type Product {
  id: ID!
  name: String!
  description: String    # nullable
  price: Float!
  imageUrl: String       # nullable
}""",
    "after_code": """# schema.graphql
type Product {
  id: ID!
  name: String!
  description: String!   # now non-null
  price: Float!
  imageUrl: String!      # now non-null
}""",
    "diff_summary": "Made description and imageUrl fields non-nullable in GraphQL Product type",
    "ground_truth": {
      "will_break": ["Existing products in DB with null description or imageUrl will cause GraphQL to return null for non-null field — runtime error: 'Cannot return null for non-nullable field'"],
      "edge_cases": ["Apollo Client and other clients that cached the old schema will have stale type information; queries expecting null handling will break"],
      "broken_pattern": "Changing nullable to non-null in GraphQL is a breaking schema change — requires ensuring all existing data has values before tightening the type",
      "next_prompt": "GraphQL is throwing 'Cannot return null for non-nullable field Product.description' for older products",
      "verified_by": "git_analogy",
      "notes": "GraphQL null-to-non-null change requires data backfill first"
    },
    "token_cost_manual_followup": 0
  },
  {
    "description": "Enum type adds value breaking exhaustive match in serializer",
    "before_code": """// order-status.ts
export enum OrderStatus {
  PENDING = 'pending',
  PROCESSING = 'processing',
  SHIPPED = 'shipped',
  DELIVERED = 'delivered',
  CANCELLED = 'cancelled',
}

// order-serializer.ts
export function getStatusLabel(status: OrderStatus): string {
  switch (status) {
    case OrderStatus.PENDING: return 'Pending';
    case OrderStatus.PROCESSING: return 'Processing';
    case OrderStatus.SHIPPED: return 'Shipped';
    case OrderStatus.DELIVERED: return 'Delivered';
    case OrderStatus.CANCELLED: return 'Cancelled';
  }
}""",
    "after_code": """// order-status.ts
export enum OrderStatus {
  PENDING = 'pending',
  PROCESSING = 'processing',
  SHIPPED = 'shipped',
  OUT_FOR_DELIVERY = 'out_for_delivery',  // new
  DELIVERED = 'delivered',
  CANCELLED = 'cancelled',
  REFUNDED = 'refunded',  // new
}

// order-serializer.ts
export function getStatusLabel(status: OrderStatus): string {
  switch (status) {
    case OrderStatus.PENDING: return 'Pending';
    case OrderStatus.PROCESSING: return 'Processing';
    case OrderStatus.SHIPPED: return 'Shipped';
    case OrderStatus.DELIVERED: return 'Delivered';
    case OrderStatus.CANCELLED: return 'Cancelled';
  }
}""",
    "diff_summary": "Added OUT_FOR_DELIVERY and REFUNDED values to OrderStatus enum without updating the switch in getStatusLabel",
    "ground_truth": {
      "will_break": ["getStatusLabel returns undefined for OUT_FOR_DELIVERY and REFUNDED — order status UI shows blank label for these orders"],
      "edge_cases": ["TypeScript will warn about non-exhaustive switch only if noImplicitReturns is enabled; without it, the bug is silent"],
      "broken_pattern": "Every switch on this enum needs updating; no central dispatch table or record type used — if there were, TS would catch it at compile time",
      "next_prompt": "Orders with 'out_for_delivery' status are showing a blank status label",
      "verified_by": "git_analogy",
      "notes": "Enum expansion with exhaustive switches is a recurring maintenance hazard"
    },
    "token_cost_manual_followup": 0
  },
  {
    "description": "Zod schema changes id field from string to UUID type",
    "before_code": """// schemas.ts
import { z } from 'zod';

export const UserSchema = z.object({
  id: z.string(),
  email: z.string().email(),
  name: z.string().min(1),
});

export type User = z.infer<typeof UserSchema>;""",
    "after_code": """// schemas.ts
import { z } from 'zod';

export const UserSchema = z.object({
  id: z.string().uuid(),  // now validates UUID format
  email: z.string().email(),
  name: z.string().min(1),
});

export type User = z.infer<typeof UserSchema>;""",
    "diff_summary": "Added .uuid() validator to UserSchema id field",
    "ground_truth": {
      "will_break": [],
      "edge_cases": ["Any test fixtures using simple string IDs like 'user-1' or 'test-id' now fail Zod parsing — all tests using non-UUID id strings break"],
      "broken_pattern": "Tightening validation on an existing schema is a breaking change if existing data uses non-UUID IDs (legacy integer IDs, slug IDs); should verify all data conforms before adding validator",
      "next_prompt": "All tests are failing with ZodError: Invalid uuid",
      "verified_by": "git_analogy",
      "notes": "Adding format validation to existing data requires checking existing data conforms first"
    },
    "token_cost_manual_followup": 0
  },
  {
    "description": "API response schema renames data field to result breaking all consumers",
    "before_code": """// api-response.ts
export interface ListResponse<T> {
  data: T[];
  total: number;
  page: number;
}

// users-api.ts
export async function listUsers(page: number): Promise<ListResponse<User>> {
  const res = await fetch(`/api/users?page=${page}`);
  return res.json();
}""",
    "after_code": """// api-response.ts
export interface ListResponse<T> {
  result: T[];  // renamed from 'data'
  total: number;
  page: number;
}

// users-api.ts
export async function listUsers(page: number): Promise<ListResponse<User>> {
  const res = await fetch(`/api/users?page=${page}`);
  return res.json();
}""",
    "diff_summary": "Renamed 'data' field to 'result' in ListResponse interface",
    "ground_truth": {
      "will_break": ["All frontend code accessing response.data from ListResponse now gets undefined — TypeScript catches this at compile time but only if running tsc; runtime would silently return undefined"],
      "edge_cases": ["If server still returns {data: [...]} but client type expects {result: [...]}, TypeScript compiles fine but runtime fails"],
      "broken_pattern": "Renaming a field in a shared API response type is a breaking API contract change — requires versioning or a deprecation period with both fields present",
      "next_prompt": "All list views are showing empty — response.data is undefined",
      "verified_by": "git_analogy",
      "notes": "Field rename in shared type is a classic breaking change"
    },
    "token_cost_manual_followup": 0
  },
  {
    "description": "Config type makes all fields required from optional",
    "before_code": """// config.ts
export interface AppConfig {
  apiUrl?: string;
  timeout?: number;
  retries?: number;
  debugMode?: boolean;
  logLevel?: 'debug' | 'info' | 'warn' | 'error';
}

const defaultConfig: AppConfig = {
  apiUrl: 'https://api.example.com',
  timeout: 5000,
  retries: 3,
};""",
    "after_code": """// config.ts
export interface AppConfig {
  apiUrl: string;
  timeout: number;
  retries: number;
  debugMode: boolean;
  logLevel: 'debug' | 'info' | 'warn' | 'error';
}

const defaultConfig: AppConfig = {
  apiUrl: 'https://api.example.com',
  timeout: 5000,
  retries: 3,
  debugMode: false,
  logLevel: 'info',
};""",
    "diff_summary": "Made all AppConfig fields required (removed optional markers)",
    "ground_truth": {
      "will_break": ["Any code creating partial config objects { apiUrl: '...' } now has TS errors for missing debugMode and logLevel; tests that mock config partially fail"],
      "edge_cases": ["Code that spreads { ...defaultConfig, ...userConfig } where userConfig is Partial<AppConfig> now gets type error"],
      "broken_pattern": "Config interfaces should stay with optional fields or use Required<> only at the point of final merging; making all fields required forces every consumer to specify everything",
      "next_prompt": "TypeScript is complaining that our test config objects are missing required properties",
      "verified_by": "git_analogy",
      "notes": "Optional-to-required change in config type breaks all partial config patterns"
    },
    "token_cost_manual_followup": 0
  },
  {
    "description": "Prisma model adds unique constraint causing upsert to fail",
    "before_code": """// schema.prisma
model UserPreference {
  id        String @id @default(cuid())
  userId    String
  key       String
  value     String
  createdAt DateTime @default(now())
}""",
    "after_code": """// schema.prisma
model UserPreference {
  id        String @id @default(cuid())
  userId    String
  key       String
  value     String
  createdAt DateTime @default(now())

  @@unique([userId, key])
}""",
    "diff_summary": "Added @@unique([userId, key]) constraint to UserPreference model",
    "ground_truth": {
      "will_break": ["Migration fails if existing data has duplicate (userId, key) pairs; upsert operations that relied on being able to create duplicate keys now fail with unique constraint violation"],
      "edge_cases": ["If code does INSERT (not upsert) for preferences, it will start failing silently for returning users on second preference write"],
      "broken_pattern": "Adding unique constraint requires deduplicating existing data first; existing code that calls create() for preferences needs to be changed to upsert() — this isn't done",
      "next_prompt": "Migration failed with 'unique constraint violation' on the preferences table",
      "verified_by": "git_analogy",
      "notes": "Unique constraint addition requires data migration and code changes in tandem"
    },
    "token_cost_manual_followup": 0
  },
  {
    "description": "TypeScript generic constraint tightening breaks existing usages",
    "before_code": """// repository.ts
export class Repository<T> {
  async findById(id: string): Promise<T | null> {
    return this.db.findOne({ id });
  }
  async save(entity: T): Promise<T> {
    return this.db.upsert(entity);
  }
}""",
    "after_code": """// repository.ts
interface HasId {
  id: string;
}

export class Repository<T extends HasId> {
  async findById(id: string): Promise<T | null> {
    return this.db.findOne({ id });
  }
  async save(entity: T): Promise<T> {
    return this.db.upsert(entity);
  }
}""",
    "diff_summary": "Added T extends HasId constraint to Repository generic class",
    "ground_truth": {
      "will_break": ["Any Repository<SomeType> where SomeType doesn't have an id: string field now gets TS error — breaking repositories using numeric IDs or UUID id fields typed as UUID not string"],
      "edge_cases": ["Repository<{ _id: string }> (MongoDB style) breaks — _id not id; Repository<{ id: number }> breaks — number not string"],
      "broken_pattern": "Tightening a generic constraint is a breaking change for all existing type parameters that don't satisfy the new constraint",
      "next_prompt": "TypeScript error: Type 'ProductEntity' does not satisfy the constraint 'HasId'",
      "verified_by": "git_analogy",
      "notes": "Generic constraint tightening is a type-level breaking change"
    },
    "token_cost_manual_followup": 0
  },
  {
    "description": "OpenAPI spec changes query param from optional to required",
    "before_code": """# openapi.yaml
paths:
  /api/items:
    get:
      parameters:
        - name: category
          in: query
          required: false
          schema:
            type: string
        - name: limit
          in: query
          required: false
          schema:
            type: integer
            default: 20""",
    "after_code": """# openapi.yaml
paths:
  /api/items:
    get:
      parameters:
        - name: category
          in: query
          required: true    # now required
          schema:
            type: string
        - name: limit
          in: query
          required: false
          schema:
            type: integer
            default: 20""",
    "diff_summary": "Made category query parameter required in the GET /api/items OpenAPI spec",
    "ground_truth": {
      "will_break": ["All clients calling /api/items without a category param now get 400 Bad Request if the server validates against the spec; mobile apps and third-party integrations break without a version bump"],
      "edge_cases": ["Auto-generated SDK clients will regenerate with category as required — breaking all existing SDK callers that omit it"],
      "broken_pattern": "Making an optional API parameter required is a breaking API change — requires a new API version (/api/v2/items) or a deprecation period",
      "next_prompt": "Our mobile app is getting 400 errors on the items endpoint after the deployment",
      "verified_by": "git_analogy",
      "notes": "Optional-to-required in public API spec is always a breaking change"
    },
    "token_cost_manual_followup": 0
  },
],
"E": [
  {
    "description": "Move authentication from middleware to service layer loses request context",
    "before_code": """# middleware/auth.py
from flask import request, g

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user = verify_token(token)
        if not user:
            return jsonify({'error': 'Unauthorized'}), 401
        g.current_user = user
        return f(*args, **kwargs)
    return decorated

# routes/orders.py
@app.route('/orders')
@require_auth
def list_orders():
    return jsonify(order_service.get_orders(g.current_user.id))""",
    "after_code": """# services/auth_service.py
class AuthService:
    def authenticate(self, token: str) -> Optional[User]:
        return verify_token(token.replace('Bearer ', ''))

# routes/orders.py
auth_service = AuthService()

@app.route('/orders')
def list_orders():
    token = request.headers.get('Authorization', '')
    user = auth_service.authenticate(token)
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
    return jsonify(order_service.get_orders(user.id))""",
    "diff_summary": "Moved authentication from @require_auth decorator middleware to inline AuthService call in each route",
    "ground_truth": {
      "will_break": [],
      "edge_cases": ["Routes that forgot to add the inline auth check now have no authentication — any new route added will silently have no auth unless developer remembers to add it manually"],
      "broken_pattern": "Decorator pattern enforced auth at the framework level; inline auth relies on developer discipline — easier to miss; g.current_user pattern removed means any code reading g.current_user elsewhere breaks",
      "next_prompt": "New routes we're adding don't seem to require authentication — did we break the auth middleware?",
      "verified_by": "git_analogy",
      "notes": "Moving auth from declarative (decorator) to imperative (inline) reduces security by default"
    },
    "token_cost_manual_followup": 0
  },
  {
    "description": "Move business logic from service to model layer couples DB and domain",
    "before_code": """# services/subscription_service.py
class SubscriptionService:
    def cancel_subscription(self, subscription_id: str, reason: str) -> None:
        sub = self.db.subscriptions.get(subscription_id)
        if sub.status == 'cancelled':
            raise ValueError("Already cancelled")
        if sub.status == 'past_due':
            self._handle_past_due_cancellation(sub)
        sub.status = 'cancelled'
        sub.cancelled_at = datetime.now()
        sub.cancellation_reason = reason
        self.db.subscriptions.save(sub)
        self.event_bus.emit('subscription.cancelled', sub)
        self.email_service.send_cancellation_email(sub.user_email)""",
    "after_code": """# models/subscription.py
class Subscription(Base):
    __tablename__ = 'subscriptions'
    # ... columns ...

    def cancel(self, reason: str) -> None:
        if self.status == 'cancelled':
            raise ValueError("Already cancelled")
        self.status = 'cancelled'
        self.cancelled_at = datetime.now()
        self.cancellation_reason = reason
        db.session.commit()
        event_bus.emit('subscription.cancelled', self)
        email_service.send_cancellation_email(self.user_email)""",
    "diff_summary": "Moved cancel_subscription logic from SubscriptionService into a cancel() method on the Subscription model",
    "ground_truth": {
      "will_break": [],
      "edge_cases": ["db.session.commit() in the model method commits all pending changes in the session, not just this subscription — other dirty objects are committed as side effect"],
      "broken_pattern": "Active Record pattern mixes persistence (db.session.commit), domain logic, events, and email in one place — violates separation of concerns; model now imports from service/infrastructure layer creating circular dependencies",
      "next_prompt": "Other database changes are getting committed when we cancel subscriptions — why?",
      "verified_by": "git_analogy",
      "notes": "Moving business logic to model creates fat model anti-pattern and session commit side effects"
    },
    "token_cost_manual_followup": 0
  },
  {
    "description": "Move validation from API layer to database layer loses API error messages",
    "before_code": """# api/products.py
@app.route('/products', methods=['POST'])
def create_product():
    data = request.json
    errors = {}
    if not data.get('name'):
        errors['name'] = 'Name is required'
    if not isinstance(data.get('price'), (int, float)) or data['price'] < 0:
        errors['price'] = 'Price must be a non-negative number'
    if errors:
        return jsonify({'errors': errors}), 422
    product = product_service.create(data)
    return jsonify(product), 201""",
    "after_code": """# models/product.py
from sqlalchemy import CheckConstraint

class Product(Base):
    __tablename__ = 'products'
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    name = Column(String, nullable=False)
    price = Column(Float, CheckConstraint('price >= 0'), nullable=False)

# api/products.py
@app.route('/products', methods=['POST'])
def create_product():
    data = request.json
    try:
        product = product_service.create(data)
        return jsonify(product), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 422""",
    "diff_summary": "Moved product validation from API layer to database constraints, removed field-specific error messages",
    "ground_truth": {
      "will_break": [],
      "edge_cases": ["Missing name field sends null to DB — IntegrityError message from SQLAlchemy exposed directly to API consumers (leaks implementation details); no field-specific errors means frontend can't highlight which field is wrong"],
      "broken_pattern": "DB constraint errors (IntegrityError) are not API errors — str(e) exposes raw SQLAlchemy/PostgreSQL error messages; API layer should translate DB errors to user-friendly messages",
      "next_prompt": "The frontend form validation highlighting stopped working — we only get a generic error now",
      "verified_by": "git_analogy",
      "notes": "Moving validation to DB layer loses field-level error detail and exposes implementation"
    },
    "token_cost_manual_followup": 0
  },
  {
    "description": "Move caching from repository to controller layer causes cache bypass",
    "before_code": """# repositories/product_repo.py
class ProductRepository:
    def find_by_id(self, product_id: str) -> Optional[Product]:
        cached = redis.get(f"product:{product_id}")
        if cached:
            return Product(**json.loads(cached))
        product = db.query(Product).filter_by(id=product_id).first()
        if product:
            redis.setex(f"product:{product_id}", 300, json.dumps(product.to_dict()))
        return product""",
    "after_code": """# controllers/product_controller.py
class ProductController:
    def get_product(self, product_id: str) -> Optional[dict]:
        cached = redis.get(f"product:{product_id}")
        if cached:
            return json.loads(cached)
        product = self.product_repo.find_by_id(product_id)
        if product:
            redis.setex(f"product:{product_id}", 300, json.dumps(product.to_dict()))
        return product.to_dict() if product else None

# repositories/product_repo.py
class ProductRepository:
    def find_by_id(self, product_id: str) -> Optional[Product]:
        return db.query(Product).filter_by(id=product_id).first()""",
    "diff_summary": "Moved Redis caching logic from ProductRepository into ProductController",
    "ground_truth": {
      "will_break": [],
      "edge_cases": ["Any other code calling product_repo.find_by_id() directly (other controllers, services, background jobs) now bypasses the cache — cache hit rate drops; cache invalidation logic needs to be added to controller too"],
      "broken_pattern": "Cache placed in controller means every access path that doesn't go through this controller misses the cache; repository was the single point for cache management — now cache logic must be duplicated everywhere product_repo is used",
      "next_prompt": "Database query load went up after the refactor — it seems like some calls are bypassing the cache",
      "verified_by": "git_analogy",
      "notes": "Moving cache from repository to controller breaks the single cache invalidation point"
    },
    "token_cost_manual_followup": 0
  },
  {
    "description": "Move email sending from synchronous to async queue loses delivery confirmation",
    "before_code": """# services/order_service.py
def place_order(user_id: str, items: list) -> Order:
    order = create_order_in_db(user_id, items)
    charge_payment(order)
    send_order_confirmation_email(order)  # synchronous
    return order  # caller knows email was sent or raises""",
    "after_code": """# services/order_service.py
from tasks import send_email_task

def place_order(user_id: str, items: list) -> Order:
    order = create_order_in_db(user_id, items)
    charge_payment(order)
    send_email_task.delay(order.id)  # fire and forget
    return order""",
    "diff_summary": "Changed order confirmation email from synchronous send to async Celery task",
    "ground_truth": {
      "will_break": [],
      "edge_cases": ["If Celery worker is down, emails are silently dropped — no fallback; if payment succeeds but Celery broker is unavailable, task is lost; no retry configuration shown"],
      "broken_pattern": "fire-and-forget without dead letter queue or retry policy; place_order no longer raises on email failure — callers that checked for exceptions from email errors now silently succeed without email",
      "next_prompt": "Some customers aren't receiving order confirmation emails — is the email queue working?",
      "verified_by": "git_analogy",
      "notes": "Async email without dead letter queue is a silent failure pattern"
    },
    "token_cost_manual_followup": 0
  },
  {
    "description": "Move rate limiting from nginx to application layer misses some entry points",
    "before_code": """# nginx.conf (removed)
# limit_req_zone $binary_remote_addr zone=api:10m rate=100r/m;
# limit_req zone=api burst=20;

# All requests rate-limited at nginx level""",
    "after_code": """# middleware/rate_limiter.py
from functools import wraps
import redis

def rate_limit(max_requests=100, window=60):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            key = f"rate:{request.remote_addr}:{f.__name__}"
            count = redis.incr(key)
            if count == 1:
                redis.expire(key, window)
            if count > max_requests:
                return jsonify({'error': 'Rate limit exceeded'}), 429
            return f(*args, **kwargs)
        return wrapper
    return decorator

# routes/api.py - only applied to some routes
@app.route('/api/search')
@rate_limit()
def search(): ...

@app.route('/api/login')  # missing @rate_limit — login not rate limited!
def login(): ...""",
    "diff_summary": "Moved rate limiting from nginx to Python application middleware, applied manually per-route",
    "ground_truth": {
      "will_break": [],
      "edge_cases": ["Login endpoint has no rate limiting — brute force attacks now possible; health check, metrics, and any internal endpoints also unprotected"],
      "broken_pattern": "Nginx rate limiting applied universally to all routes; application-level requires opt-in per route — any new route added is unprotected by default; request.remote_addr can be spoofed via X-Forwarded-For",
      "next_prompt": "We need to add rate limiting to the login endpoint — brute force protection is missing",
      "verified_by": "git_analogy",
      "notes": "Moving from infrastructure to application-level security requires opt-in which creates gaps"
    },
    "token_cost_manual_followup": 0
  },
  {
    "description": "Move logging from application to infrastructure layer loses structured context",
    "before_code": """# services/payment_service.py
import structlog

logger = structlog.get_logger()

def process_payment(order_id: str, amount: float, user_id: str) -> PaymentResult:
    logger.info("payment.start", order_id=order_id, amount=amount, user_id=user_id)
    result = payment_gateway.charge(amount)
    if result.success:
        logger.info("payment.success", order_id=order_id, transaction_id=result.transaction_id)
    else:
        logger.error("payment.failed", order_id=order_id, reason=result.error_code)
    return result""",
    "after_code": """# infrastructure/logging_middleware.py
import logging

@app.before_request
def log_request():
    logging.info(f"{request.method} {request.path}")

@app.after_request
def log_response(response):
    logging.info(f"Response: {response.status_code}")
    return response

# services/payment_service.py (logging removed)
def process_payment(order_id: str, amount: float, user_id: str) -> PaymentResult:
    result = payment_gateway.charge(amount)
    return result""",
    "diff_summary": "Moved logging to request/response middleware, removed structured business event logging from payment service",
    "ground_truth": {
      "will_break": [],
      "edge_cases": ["Payment failures now produce only 'Response: 200' log (charge failures may still return 200 with error in body) — no payment failure alerts possible"],
      "broken_pattern": "HTTP-level logging captures what happened at the transport layer; structured business event logging captures why it happened with domain context; they serve different purposes and both are needed",
      "next_prompt": "We can't tell from logs whether a payment succeeded or failed — we lost the transaction IDs",
      "verified_by": "git_analogy",
      "notes": "Infrastructure logging replaces but cannot substitute for domain event logging"
    },
    "token_cost_manual_followup": 0
  },
  {
    "description": "Move authorization from routes to database queries loses multi-tenant isolation",
    "before_code": """# routes/documents.py
@app.route('/documents')
@require_auth
def list_documents():
    # Route-level: only show docs for current user's organization
    docs = document_service.get_documents(org_id=g.current_user.org_id)
    return jsonify(docs)

# services/document_service.py
def get_documents(org_id: str) -> list:
    return db.query(Document).filter_by(org_id=org_id).all()""",
    "after_code": """# routes/documents.py
@app.route('/documents')
@require_auth
def list_documents():
    docs = document_service.get_documents(user=g.current_user)
    return jsonify(docs)

# services/document_service.py
def get_documents(user=None, org_id=None) -> list:
    query = db.query(Document)
    if user and user.role != 'superadmin':
        query = query.filter_by(org_id=user.org_id)
    elif org_id:
        query = query.filter_by(org_id=org_id)
    return query.all()""",
    "diff_summary": "Moved org_id filtering from explicit route parameter to conditional logic in get_documents based on user role",
    "ground_truth": {
      "will_break": [],
      "edge_cases": ["If user.role check fails (None, unexpected value), query falls through with no org filter — returns all documents from all orgs; role string case sensitivity ('Superadmin' vs 'superadmin') bypasses restriction"],
      "broken_pattern": "Explicit org_id parameter was safe by default — caller must supply it; new role-based conditional is secure by exception — requires correct role check; any code calling get_documents(org_id=None) now returns all documents",
      "next_prompt": "In testing I'm seeing documents from other organizations appearing in the list",
      "verified_by": "git_analogy",
      "notes": "Secure-by-default replaced by secure-by-exception — multi-tenant isolation at risk"
    },
    "token_cost_manual_followup": 0
  },
  {
    "description": "Move session management from server to client JWT increases token scope",
    "before_code": """# Session-based auth (server side)
# sessions stored in Redis, revocable immediately

@app.route('/login', methods=['POST'])
def login():
    user = authenticate(request.json['email'], request.json['password'])
    session_id = create_session(user.id)  # stored in Redis with 1hr TTL
    response.set_cookie('session_id', session_id, httponly=True, secure=True)
    return jsonify({'status': 'ok'})""",
    "after_code": """# JWT-based auth (client side)
import jwt

@app.route('/login', methods=['POST'])
def login():
    user = authenticate(request.json['email'], request.json['password'])
    token = jwt.encode({
        'user_id': user.id,
        'role': user.role,
        'org_id': user.org_id,
        'permissions': user.permissions,
        'exp': datetime.now() + timedelta(hours=24)
    }, SECRET_KEY)
    return jsonify({'token': token})""",
    "diff_summary": "Migrated from server-side sessions to JWT tokens containing user role, org, and permissions",
    "ground_truth": {
      "will_break": [],
      "edge_cases": ["No revocation mechanism — compromised tokens valid for 24hrs; if user role changes (e.g. deprovisioned admin), old token still grants admin access until expiry"],
      "broken_pattern": "Sessions were immediately revocable (delete from Redis); JWTs are not revocable without a blacklist — 24hr expiry means a fired employee retains access for up to 24 hours; permissions baked into token get stale",
      "next_prompt": "How do we invalidate JWT tokens when a user is suspended or their role changes?",
      "verified_by": "git_analogy",
      "notes": "JWT adoption without token revocation is a common auth architecture mistake"
    },
    "token_cost_manual_followup": 0
  },
  {
    "description": "Move file processing from request-time to background worker loses progress feedback",
    "before_code": """# api/import.py
@app.route('/import/csv', methods=['POST'])
def import_csv():
    file = request.files['file']
    results = process_csv_import(file)  # synchronous, can take 30s
    return jsonify({
        'imported': results.success_count,
        'failed': results.failed_count,
        'errors': results.errors  # specific row errors returned
    })""",
    "after_code": """# api/import.py
from tasks import process_csv_task

@app.route('/import/csv', methods=['POST'])
def import_csv():
    file = request.files['file']
    file_path = save_to_temp(file)
    job_id = process_csv_task.delay(file_path)
    return jsonify({'job_id': str(job_id), 'status': 'processing'})""",
    "diff_summary": "Changed CSV import from synchronous processing to async Celery background task",
    "ground_truth": {
      "will_break": [],
      "edge_cases": ["No endpoint to check job status or retrieve results — frontend gets job_id but nowhere to poll; temp file may be deleted before worker processes it if cleanup runs first"],
      "broken_pattern": "Async job requires a status endpoint (/import/status/{job_id}) and result storage — neither implemented; the API contract changed from synchronous result to async job without frontend coordination",
      "next_prompt": "How do I check if the import finished? The response only gives me a job_id but there's no status endpoint",
      "verified_by": "git_analogy",
      "notes": "Async migration requires building status/result retrieval — half-implemented here"
    },
    "token_cost_manual_followup": 0
  },
  {
    "description": "Move error handling from individual services to global handler swallows specific errors",
    "before_code": """# services/inventory_service.py
class InsufficientStockError(Exception):
    def __init__(self, product_id: str, requested: int, available: int):
        self.product_id = product_id
        self.requested = requested
        self.available = available

def reserve_inventory(product_id: str, quantity: int) -> None:
    stock = get_stock(product_id)
    if stock < quantity:
        raise InsufficientStockError(product_id, quantity, stock)
    # ... reserve

# routes/orders.py
@app.route('/orders', methods=['POST'])
def create_order():
    try:
        reserve_inventory(product_id, qty)
        return jsonify(order), 201
    except InsufficientStockError as e:
        return jsonify({'error': 'insufficient_stock', 'available': e.available}), 409""",
    "after_code": """# middleware/error_handler.py
@app.errorhandler(Exception)
def handle_error(e):
    return jsonify({'error': str(e)}), 500

# routes/orders.py (try/except removed)
@app.route('/orders', methods=['POST'])
def create_order():
    reserve_inventory(product_id, qty)
    return jsonify(order), 201""",
    "diff_summary": "Replaced per-route error handling with global exception handler middleware",
    "ground_truth": {
      "will_break": ["InsufficientStockError now returns 500 instead of 409 — frontend cannot distinguish 'out of stock' from 'server error'; available stock quantity no longer in response"],
      "edge_cases": ["str(InsufficientStockError) leaks internal details (product_id, quantities) in the 500 response; any exception now returns 500 — including validation errors that should be 422"],
      "broken_pattern": "Global catch-all handler is good as a safety net but should not replace specific error handling; different exception types need different HTTP status codes and response shapes",
      "next_prompt": "The add-to-cart flow is getting a 500 error instead of showing 'out of stock' — what happened?",
      "verified_by": "git_analogy",
      "notes": "Global error handler replacing specific handlers loses HTTP semantic meaning"
    },
    "token_cost_manual_followup": 0
  },
  {
    "description": "Move search from SQL LIKE to Elasticsearch loses exact-match behavior",
    "before_code": """# services/search_service.py
def search_customers(query: str, org_id: str) -> list:
    return db.execute(
        "SELECT * FROM customers WHERE org_id = %s AND (name ILIKE %s OR email ILIKE %s)",
        (org_id, f"%{query}%", f"%{query}%")
    )""",
    "after_code": """# services/search_service.py
from elasticsearch import Elasticsearch

es = Elasticsearch()

def search_customers(query: str, org_id: str) -> list:
    result = es.search(index='customers', body={
        'query': {
            'multi_match': {
                'query': query,
                'fields': ['name', 'email']
            }
        }
    })
    return [hit['_source'] for hit in result['hits']['hits']]""",
    "diff_summary": "Replaced SQL LIKE search with Elasticsearch multi_match query",
    "ground_truth": {
      "will_break": ["org_id filter removed — search returns customers from all organizations; multi-tenant data isolation broken"],
      "edge_cases": ["Elasticsearch index may not exist yet or may be out of sync with DB — no fallback; ES unavailable causes search to throw uncaught exception"],
      "broken_pattern": "Critical security regression: org_id scoping removed; ES multi_match uses relevance scoring (fuzzy) vs SQL ILIKE (exact substring) — behavior change not communicated; no ES index management or sync shown",
      "next_prompt": "Customer search is returning results from other companies' accounts",
      "verified_by": "git_analogy",
      "notes": "Architecture migration dropped the security filter — critical multi-tenant isolation bug"
    },
    "token_cost_manual_followup": 0
  },
]
}

def count_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token."""
    return max(1, len(text) // 4)

def generate_cases():
    os.makedirs(TEST_CASES_DIR, exist_ok=True)
    index = []
    total = 0

    for stratum_key, stratum_info in STRATA.items():
        cases = CASES[stratum_key]
        for i, case_data in enumerate(cases):
            case_id = f"case_{stratum_key}_{i+1:03d}"
            next_prompt = case_data["ground_truth"]["next_prompt"]
            token_cost = count_tokens(next_prompt) + 15

            case = {
                "id": case_id,
                "stratum": stratum_key,
                "difficulty": stratum_info["difficulty"],
                "language": stratum_info["language"],
                "change_type": stratum_info["change_type"],
                "description": case_data["description"],
                "before_code": case_data["before_code"],
                "after_code": case_data["after_code"],
                "diff_summary": case_data["diff_summary"],
                "ground_truth": case_data["ground_truth"],
                "token_cost_manual_followup": token_cost,
            }

            out_path = os.path.join(TEST_CASES_DIR, f"{case_id}.json")
            with open(out_path, "w") as f:
                json.dump(case, f, indent=2)

            index.append({"id": case_id, "stratum": stratum_key})
            total += 1

    index_path = os.path.join(BENCHMARK_DIR, "data", "ground_truth", "index.json")
    with open(index_path, "w") as f:
        json.dump(index, f, indent=2)

    print(f"✓ Phase 1 complete — {total} items processed")
    return total

if __name__ == "__main__":
    n = generate_cases()
    if n != 60:
        print(f"WARNING: Expected 60 cases, got {n}", file=sys.stderr)
        sys.exit(1)
