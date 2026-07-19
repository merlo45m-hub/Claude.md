import * as d3 from 'd3-force';

interface MiniNode extends d3.SimulationNodeDatum {
  x: number;
  y: number;
}

/**
 * Compute positions for N dots arranged radially around a center point.
 * Uses d3 forceCollide to resolve overlaps. Synchronous — returns final positions.
 */
export function computeMiniLayout(
  count: number,
  center: { x: number; y: number },
  radius: number,
  dotRadius: number = 4,
): { x: number; y: number }[] {
  if (count === 0) return [];

  if (count === 1) {
    return [{ x: center.x, y: center.y }];
  }

  // Place nodes radially
  const nodes: MiniNode[] = [];
  for (let i = 0; i < count; i++) {
    const angle = (i / count) * 2 * Math.PI;
    // Spread across the radius, with some randomness for organic feel
    const r = count <= 6
      ? radius * 0.5
      : radius * (0.3 + (i % 3) * 0.25);
    nodes.push({
      x: center.x + Math.cos(angle) * r,
      y: center.y + Math.sin(angle) * r,
    });
  }

  // Run a quick simulation to resolve overlaps
  const sim = d3.forceSimulation<MiniNode>(nodes)
    .force('collide', d3.forceCollide<MiniNode>().radius(dotRadius * 2.5).strength(0.8))
    .force('x', d3.forceX(center.x).strength(0.15))
    .force('y', d3.forceY(center.y).strength(0.15))
    .stop();

  // Run synchronously
  sim.tick(20);

  return nodes.map(n => ({ x: n.x, y: n.y }));
}
