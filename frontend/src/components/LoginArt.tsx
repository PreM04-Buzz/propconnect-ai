/**
 * The illustration beside the sign-in form: a city skyline at dusk with a street
 * of homes in front, one of them for sale. On load, a broker and a client meet
 * there and shake hands, and the sign flips to SOLD (about 5 seconds, once). Original artwork drawn in SVG, so it
 * needs no image files, stays sharp at any size and uses the app's own colors.
 */

// A tiny deterministic random generator, so the lit windows are the same on every load.
function rng(seed: number) {
  let s = seed;
  return () => {
    s = (s * 16807) % 2147483647;
    return (s - 1) / 2147483646;
  };
}

type Tower = { x: number; w: number; h: number };

function towerWindows(t: Tower, base: number, rand: () => number, lit: number) {
  const out = [];
  for (let y = base - t.h + 14; y < base - 10; y += 13) {
    for (let x = t.x + 6; x < t.x + t.w - 7; x += 10) {
      if (rand() < lit) out.push(<rect key={`${x}-${y}`} x={x} y={y} width={4} height={6} rx={0.5} />);
    }
  }
  return out;
}

const FAR: Tower[] = [
  { x: -10, w: 60, h: 210 }, { x: 46, w: 44, h: 260 }, { x: 86, w: 70, h: 190 }, { x: 150, w: 38, h: 300 },
  { x: 184, w: 64, h: 230 }, { x: 244, w: 50, h: 340 }, { x: 290, w: 72, h: 250 }, { x: 358, w: 46, h: 290 },
  { x: 400, w: 68, h: 205 }, { x: 464, w: 52, h: 320 }, { x: 512, w: 60, h: 240 }, { x: 568, w: 50, h: 275 },
];
const NEAR: Tower[] = [
  { x: 20, w: 74, h: 170 }, { x: 118, w: 58, h: 225 }, { x: 206, w: 80, h: 160 }, { x: 318, w: 62, h: 250 },
  { x: 412, w: 84, h: 175 }, { x: 520, w: 66, h: 205 },
];

function House({ x, w, h, roof, sale = false }: { x: number; w: number; h: number; roof: number; sale?: boolean }) {
  const ground = 640;
  const top = ground - h;
  const doorW = w * 0.2;
  return (
    <g>
      <polygon points={`${x - 8},${top} ${x + w / 2},${top - roof} ${x + w + 8},${top}`} fill="#15212c" />
      <rect x={x} y={top} width={w} height={h} fill={sale ? "#2c4155" : "#24374a"} />
      <rect x={x + w * 0.14} y={top + h * 0.2} width={w * 0.22} height={h * 0.24} fill="#e9b85c" opacity={0.9} />
      <rect x={x + w * 0.64} y={top + h * 0.2} width={w * 0.22} height={h * 0.24} fill="#e9b85c" opacity={sale ? 0.9 : 0.35} />
      <rect x={x + w / 2 - doorW / 2} y={ground - h * 0.42} width={doorW} height={h * 0.42}
            fill={sale ? "#a8741a" : "#1a2836"} />
      {sale && (
        <g>
          <rect x={x + w + 22} y={ground - 62} width={3} height={62} fill="#c9cfd4" />
          <rect x={x + w + 22} y={ground - 62} width={44} height={3} fill="#c9cfd4" />
        </g>
      )}
    </g>
  );
}

/** The sign on the house for sale. It flips from "For sale" to "SOLD" once the deal is done. */
function SaleSign() {
  return (
    <g className="deal-sign">
      <rect className="deal-board" x={420} y={582} width={36} height={24} rx={2} />
      <text className="deal-sale" x={438} y={598} textAnchor="middle">For sale</text>
      <text className="deal-sold" x={438} y={599} textAnchor="middle">SOLD</text>
    </g>
  );
}

type PersonLook = { suit: string; legs: [string, string]; skin: string; hair: string; broker?: boolean };

/** A simple flat figure facing right, feet at (0, 0). The arm swings forward for the handshake. */
function Person({ look }: { look: PersonLook }) {
  return (
    <>
      <g className="deal-leg deal-leg-a"><rect x={-6} y={-24} width={5.5} height={24} rx={2} fill={look.legs[0]} /></g>
      <g className="deal-leg deal-leg-b"><rect x={0.5} y={-24} width={5.5} height={24} rx={2} fill={look.legs[1]} /></g>
      <rect x={-9} y={-50} width={18} height={28} rx={look.broker ? 4 : 5} fill={look.suit} />
      {look.broker && (
        <>
          <polygon points="-3,-50 3,-50 0,-40" fill="#f5f6f3" />
          <rect x={-1} y={-45} width={2} height={9} fill="#e0a94a" />
          <rect x={-15} y={-44} width={8} height={11} rx={1.5} fill="#e0a94a" />
        </>
      )}
      <circle cx={0} cy={-58} r={7.5} fill={look.skin} />
      {look.broker
        ? <path d="M-7.5,-60 a7.5,7.5 0 0 1 15,0 l0,-1 a7.5,6 0 0 0 -15,0z" fill={look.hair} />
        : <path d="M-8,-58 a8,8 0 0 1 16,0 l0,-4 a8,7 0 0 0 -16,0z" fill={look.hair} />}
      <g className="deal-arm">
        <rect x={5} y={-48} width={5} height={21} rx={2.5} fill={look.suit} />
        <circle cx={7.5} cy={-27} r={2.8} fill={look.skin} />
      </g>
    </>
  );
}

const BROKER: PersonLook = { suit: "#4b6b86", legs: ["#24384a", "#2b4256"], skin: "#c68a5e", hair: "#2a1f1a", broker: true };
const CLIENT: PersonLook = { suit: "#e8dcc4", legs: ["#4f6d88", "#5d7a94"], skin: "#8d5a3b", hair: "#1c1410" };

/** A broker and a client walk up to the house for sale and shake hands; the sign then flips to SOLD. */
function Deal() {
  const sparkle = (x: number, y: number, r: number, cls: string) => (
    <path className={`deal-spark ${cls}`}
          d={`M${x},${y} l${r * 0.33},${r} ${r},${r * 0.33} ${-r},${r * 0.33} ${-r * 0.33},${r} ${-r * 0.33},${-r} ${-r},${-r * 0.33} ${r},${-r * 0.33}z`} />
  );
  return (
    <g>
      <SaleSign />
      <g className="deal-walk-broker"><g transform="translate(300,660) scale(1.25)"><Person look={BROKER} /></g></g>
      <g className="deal-walk-client"><g transform="translate(364,660) scale(-1.25,1.25)"><Person look={CLIENT} /></g></g>
      <g fill="#e0a94a">
        {sparkle(332, 618, 6, "deal-spark-1")}
        {sparkle(318, 627, 4, "deal-spark-2")}
        {sparkle(348, 625, 4, "deal-spark-3")}
      </g>
    </g>
  );
}

export function LoginArt() {
  const rand = rng(42);
  return (
    <svg className="login-art-svg deal-play" viewBox="0 0 600 700" preserveAspectRatio="xMidYMax slice" role="img"
         aria-label="A broker and a client shake hands in front of a house, and the sign changes from For sale to Sold">
      <defs>
        <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#1c2b3a" />
          <stop offset="0.65" stopColor="#2a4054" />
          <stop offset="1" stopColor="#4a5d6b" />
        </linearGradient>
      </defs>
      <rect width="600" height="700" fill="url(#sky)" />
      <circle cx="470" cy="150" r="34" fill="#f3e7cf" opacity="0.85" />

      {/* Far skyline, faint windows */}
      <g fill="#253a4d">{FAR.map((t, i) => <rect key={i} x={t.x} y={560 - t.h} width={t.w} height={t.h} />)}</g>
      <g fill="#e9b85c" opacity="0.35">{FAR.map((t) => towerWindows(t, 560, rand, 0.22))}</g>

      {/* Nearer buildings, brighter windows */}
      <g fill="#1f3043">{NEAR.map((t, i) => <rect key={i} x={t.x} y={600 - t.h} width={t.w} height={t.h} />)}</g>
      <g fill="#e9b85c" opacity="0.75">{NEAR.map((t) => towerWindows(t, 600, rand, 0.3))}</g>

      {/* The street */}
      <rect x="0" y="600" width="600" height="100" fill="#172430" />
      <circle cx="40" cy="606" r="26" fill="#1d2e26" />
      <circle cx="232" cy="610" r="22" fill="#1d2e26" />
      <circle cx="560" cy="604" r="30" fill="#1d2e26" />
      <House x={70} w={92} h={74} roof={36} />
      <House x={272} w={118} h={96} roof={46} sale />
      <House x={470} w={84} h={70} roof={34} />
      <Deal />
      <rect x="0" y="640" width="600" height="60" fill="#121c25" />
      <rect x="0" y="664" width="600" height="2" fill="#a8741a" opacity="0.5" />
    </svg>
  );
}
