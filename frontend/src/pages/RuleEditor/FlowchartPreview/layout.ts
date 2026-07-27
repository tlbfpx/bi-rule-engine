/**
 * 手动布局辅助。图的形状受控（纵向链 + 至多 2~3 列分支），无需 dagre。
 */

/** 列 X 坐标常量 */
export const MAIN_X = 0;
export const OFFRAMP_X = 320;
export const OUTPUT_X = 640;

/** 每个节点纵向步进 */
export const Y_STEP = 130;

export interface Point {
  x: number;
  y: number;
}

/** 单列纵向布局：返回 count 个点的坐标。 */
export function verticalLayout(count: number, x = MAIN_X, startY = 0, yStep = Y_STEP): Point[] {
  return Array.from({ length: count }, (_, i) => ({ x, y: startY + i * yStep }));
}
