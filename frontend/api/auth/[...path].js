import crypto from 'node:crypto';

const COOKIE_NAME = process.env.ACCESS_GATE_COOKIE_NAME || 'goala_access';
const SESSION_SECRET = process.env.ACCESS_GATE_SESSION_SECRET || '';
const SESSION_TTL_SECONDS = Number(process.env.ACCESS_GATE_SESSION_TTL_SECONDS || '604800');

function parseTokenHashes(envVar) {
  return (process.env[envVar] || '')
    .split(',')
    .map((value) => value.trim().toLowerCase())
    .filter(Boolean);
}

function buildAdminTokenHashes() {
  const seen = new Set();
  const hashes = [];

  for (const hashValue of [
    ...parseTokenHashes('ACCESS_GATE_ADMIN_TOKEN_HASHES'),
    ...parseTokenHashes('ACCESS_GATE_TOKEN_HASHES'),
  ]) {
    if (!seen.has(hashValue)) {
      seen.add(hashValue);
      hashes.push(hashValue);
    }
  }

  return hashes;
}

const ADMIN_TOKEN_HASHES = buildAdminTokenHashes();
const OPERATOR_TOKEN_HASHES = parseTokenHashes('ACCESS_GATE_OPERATOR_TOKEN_HASHES');

function isAuthEnabled() {
  return Boolean(SESSION_SECRET && (ADMIN_TOKEN_HASHES.length > 0 || OPERATOR_TOKEN_HASHES.length > 0));
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

function resolveRoleFromToken(token) {
  const submittedHash = hashToken(token.trim());

  if (ADMIN_TOKEN_HASHES.some((hashValue) => safeEquals(hashValue, submittedHash))) {
    return 'admin';
  }

  if (OPERATOR_TOKEN_HASHES.some((hashValue) => safeEquals(hashValue, submittedHash))) {
    return 'operator';
  }

  return null;
}

function decodeVerifiedPayload(cookieValue) {
  if (!isAuthEnabled() || !cookieValue || typeof cookieValue !== 'string') {
    return null;
  }

  try {
    const [payloadSegment, signatureSegment] = cookieValue.split('.', 2);
    if (!payloadSegment || !signatureSegment) {
      return null;
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
      return null;
    }

    const payload = JSON.parse(base64UrlDecode(payloadSegment).toString('utf8'));
    if (Number(payload.exp || 0) <= Math.floor(Date.now() / 1000)) {
      return null;
    }

    return payload;
  } catch {
    return null;
  }
}

function createCookieValue(role) {
  const issuedAt = Math.floor(Date.now() / 1000);
  const payload = JSON.stringify({
    iat: issuedAt,
    exp: issuedAt + SESSION_TTL_SECONDS,
    role,
  });
  const payloadSegment = base64UrlEncode(payload);
  const signature = crypto
    .createHmac('sha256', SESSION_SECRET)
    .update(payloadSegment, 'ascii')
    .digest();
  return `${payloadSegment}.${base64UrlEncode(signature)}`;
}

function verifyCookieValue(cookieValue) {
  return decodeVerifiedPayload(cookieValue) !== null;
}

function getRoleFromCookie(cookieValue) {
  const payload = decodeVerifiedPayload(cookieValue);
  if (!payload) {
    return null;
  }

  const role = payload.role;
  return role === 'admin' || role === 'operator' ? role : null;
}

function safeEquals(left, right) {
  const leftBuffer = Buffer.from(left, 'utf8');
  const rightBuffer = Buffer.from(right, 'utf8');
  return leftBuffer.length === rightBuffer.length && crypto.timingSafeEqual(leftBuffer, rightBuffer);
}

function buildCookieOptions(cookieValue, maxAgeSeconds) {
  return [
    `${COOKIE_NAME}=${cookieValue}`,
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

function resolveRequestPath(req) {
  if (Array.isArray(req.query?.path)) {
    return `/${req.query.path.join('/')}`;
  }

  if (typeof req.query?.path === 'string' && req.query.path.trim()) {
    return `/${req.query.path.trim()}`;
  }

  try {
    return new URL(req.url, 'http://localhost').pathname;
  } catch {
    return req.url || '/api/auth';
  }
}

export default async function handler(req, res) {
  const pathname = resolveRequestPath(req).replace(/\/$/, '');
  const isLogin = pathname === '/login' || pathname.endsWith('/login');
  const isMe = pathname === '/me' || pathname.endsWith('/me');
  const isLogout = pathname === '/logout' || pathname.endsWith('/logout');

  if (!isAuthEnabled()) {
    res.status(503).json({ detail: 'Access gate is not configured' });
    return;
  }

  if (req.method === 'GET' && isMe) {
    const cookieValue = req.cookies?.[COOKIE_NAME];
    const authenticated = verifyCookieValue(cookieValue);
    res.status(200).json({
      authenticated,
      role: authenticated ? getRoleFromCookie(cookieValue) : null,
    });
    return;
  }

  if (req.method === 'POST' && isLogin) {
    const { token } = await readJsonBody(req);
    if (typeof token !== 'string' || !token.trim()) {
      res.status(401).json({ detail: 'Invalid access token' });
      return;
    }

    const role = resolveRoleFromToken(token);
    if (!role) {
      res.status(401).json({ detail: 'Invalid access token' });
      return;
    }

    const cookieValue = createCookieValue(role);
    res.setHeader('Set-Cookie', buildCookieOptions(cookieValue, SESSION_TTL_SECONDS));
    res.status(200).json({ authenticated: true, role });
    return;
  }

  if (req.method === 'POST' && isLogout) {
    res.setHeader('Set-Cookie', clearCookieOptions());
    res.status(200).json({ authenticated: false, role: null });
    return;
  }

  res.status(405).json({ detail: 'Method not allowed' });
}
