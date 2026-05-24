import { NextRequest, NextResponse } from 'next/server';

const COOKIE_NAME = process.env.ACCESS_GATE_COOKIE_NAME || 'goala_access';
const SESSION_SECRET = process.env.ACCESS_GATE_SESSION_SECRET || '';

function base64UrlToBase64(value: string): string {
  const normalized = value.replace(/-/g, '+').replace(/_/g, '/');
  return `${normalized}${'='.repeat((4 - (normalized.length % 4)) % 4)}`;
}

function base64UrlDecodeToText(value: string): string {
  return atob(base64UrlToBase64(value));
}

async function verifyCookieValue(cookieValue: string | undefined): Promise<boolean> {
  if (!SESSION_SECRET || !cookieValue) {
    return false;
  }

  const [payloadSegment, signatureSegment] = cookieValue.split('.', 2);
  if (!payloadSegment || !signatureSegment) {
    return false;
  }

  const encoder = new TextEncoder();
  const key = await crypto.subtle.importKey(
    'raw',
    encoder.encode(SESSION_SECRET),
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['verify']
  );

  const signature = Uint8Array.from(atob(base64UrlToBase64(signatureSegment)), (character) => character.charCodeAt(0));
  const verified = await crypto.subtle.verify(
    'HMAC',
    key,
    signature,
    encoder.encode(payloadSegment)
  );

  if (!verified) {
    return false;
  }

  try {
    const payloadJson = base64UrlDecodeToText(payloadSegment);
    const payload = JSON.parse(payloadJson);
    return Number(payload.exp || 0) > Math.floor(Date.now() / 1000);
  } catch {
    return false;
  }
}

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  if (
    pathname.startsWith('/api/auth') ||
    pathname.startsWith('/assets/') ||
    pathname === '/favicon.ico' ||
    pathname === '/vite.svg' ||
    pathname === '/login'
  ) {
    return NextResponse.next();
  }

  if (await verifyCookieValue(request.cookies.get(COOKIE_NAME)?.value)) {
    return NextResponse.next();
  }

  const loginUrl = request.nextUrl.clone();
  loginUrl.pathname = '/login';
  loginUrl.search = '';
  return NextResponse.redirect(loginUrl);
}

export const config = {
  matcher: ['/((?!.*\\.).*)', '/'],
};