import crypto from 'node:crypto';

const COOKIE_NAME = process.env.ACCESS_GATE_COOKIE_NAME || 'goala_access';
const SESSION_SECRET = process.env.ACCESS_GATE_SESSION_SECRET || '';
const TOKEN_HASHES = (process.env.ACCESS_GATE_TOKEN_HASHES || '')
  .split(',')
  .map((value) => value.trim().toLowerCase())
  .filter(Boolean);
const SESSION_TTL_SECONDS = Number(process.env.ACCESS_GATE_SESSION_TTL_SECONDS || '604800');

function isAuthEnabled() {
  return Boolean(SESSION_SECRET && TOKEN_HASHES.length > 0);
}

function hashToken(token) {
  return crypto.createHash('sha256').update(token, 'utf8').digest('hex');
}

function base64UrlEncode(buffer) {
  return Buffer.from(buffer).toString('base64url');
}

function base64UrlDecode(value) {
  return Buffer.from(value, 'base64url');
}

function createCookieValue() {
  const issuedAt = Math.floor(Date.now() / 1000);
  const payload = JSON.stringify({
    iat: issuedAt,
    exp: issuedAt + SESSION_TTL_SECONDS,
  });
  const payloadSegment = base64UrlEncode(payload);
  const signature = crypto
    .createHmac('sha256', SESSION_SECRET)
    .update(payloadSegment, 'ascii')
    .digest();
  return `${payloadSegment}.${base64UrlEncode(signature)}`;
}

function verifyCookieValue(cookieValue) {
  if (!isAuthEnabled() || !cookieValue || typeof cookieValue !== 'string') {
    return false;
  }

  try {
    const [payloadSegment, signatureSegment] = cookieValue.split('.', 2);
    if (!payloadSegment || !signatureSegment) {
      return false;
    }

    const expectedSignature = crypto
      .createHmac('sha256', SESSION_SECRET)
      .update(payloadSegment, 'ascii')
      .digest();
    const providedSignature = base64UrlDecode(signatureSegment);

    if (
      expectedSignature.length !== providedSignature.length ||
      !crypto.timingSafeEqual(expectedSignature, providedSignature)
    ) {
      return false;
    }

    const payload = JSON.parse(base64UrlDecode(payloadSegment).toString('utf8'));
    return Number(payload.exp || 0) > Math.floor(Date.now() / 1000);
  } catch {
    return false;
  }
}

function safeEquals(left, right) {
  const leftBuffer = Buffer.from(left, 'utf8');
  const rightBuffer = Buffer.from(right, 'utf8');
  return leftBuffer.length === rightBuffer.length && crypto.timingSafeEqual(leftBuffer, rightBuffer);
}

function buildCookieOptions(maxAgeSeconds) {
  return [
    `${COOKIE_NAME}=${createCookieValue()}`,
    'Path=/',
    'HttpOnly',
    'Secure',
    'SameSite=Lax',
    `Max-Age=${maxAgeSeconds}`,
  ].join('; ');
}

function clearCookieOptions() {
  return [
    `${COOKIE_NAME}=`,
    'Path=/',
    'HttpOnly',
    'Secure',
    'SameSite=Lax',
    'Max-Age=0',
  ].join('; ');
}

async function readJsonBody(req) {
  const chunks = [];
  for await (const chunk of req) {
    chunks.push(Buffer.from(chunk));
  }
  const rawBody = Buffer.concat(chunks).toString('utf8') || '{}';
  return JSON.parse(rawBody);
}

export default async function handler(req, res) {
  const pathname = req.url || '/api/auth';
  const isLogin = pathname.endsWith('/login');
  const isMe = pathname.endsWith('/me');
  const isLogout = pathname.endsWith('/logout');

  if (!isAuthEnabled()) {
    res.status(503).json({ detail: 'Access gate is not configured' });
    return;
  }

  if (req.method === 'GET' && isMe) {
    const authenticated = verifyCookieValue(req.cookies?.[COOKIE_NAME]);
    res.status(200).json({ authenticated });
    return;
  }

  if (req.method === 'POST' && isLogin) {
    const { token } = await readJsonBody(req);
    if (typeof token !== 'string' || !token.trim()) {
      res.status(401).json({ detail: 'Invalid access token' });
      return;
    }

    const submittedHash = hashToken(token.trim());
    const matches = TOKEN_HASHES.some((hashValue) => safeEquals(hashValue, submittedHash));
    if (!matches) {
      res.status(401).json({ detail: 'Invalid access token' });
      return;
    }

    res.setHeader('Set-Cookie', buildCookieOptions(SESSION_TTL_SECONDS));
    res.status(200).json({ authenticated: true });
    return;
  }

  if (req.method === 'POST' && isLogout) {
    res.setHeader('Set-Cookie', clearCookieOptions());
    res.status(200).json({ authenticated: false });
    return;
  }

  res.status(405).json({ detail: 'Method not allowed' });
}