import type { CanvasRenderingTarget2D } from "fancy-canvas";
import {
  type ISeriesPrimitive,
  type IPrimitivePaneView,
  type IPrimitivePaneRenderer,
  type SeriesAttachedParameter,
  type IChartApiBase,
  type ISeriesApi,
  type SeriesType,
  type Time,
  type PrimitivePaneViewZOrder,
} from "lightweight-charts";

export interface VolumeBar {
  time: number;
  open: number;
  close: number;
  high: number;
  low: number;
  volume: number;
}

interface PriceBin {
  price: number;
  buyVolume: number;
  sellVolume: number;
}

const NUM_BINS = 40;
const MAX_BAR_WIDTH_PCT = 0.25;
const BUY_COLOR = "rgba(54,187,128,0.5)";
const SELL_COLOR = "rgba(255,113,52,0.5)";

function computeBins(bars: VolumeBar[]): PriceBin[] {
  if (bars.length === 0) return [];

  let minPrice = Infinity;
  let maxPrice = -Infinity;
  for (const b of bars) {
    if (b.low < minPrice) minPrice = b.low;
    if (b.high > maxPrice) maxPrice = b.high;
  }

  const range = maxPrice - minPrice;
  if (range <= 0) return [];

  const binSize = range / NUM_BINS;
  const bins: PriceBin[] = [];
  for (let i = 0; i < NUM_BINS; i++) {
    bins.push({
      price: minPrice + binSize * (i + 0.5),
      buyVolume: 0,
      sellVolume: 0,
    });
  }

  for (const bar of bars) {
    const idx = Math.min(
      Math.floor((bar.close - minPrice) / binSize),
      NUM_BINS - 1,
    );
    if (idx < 0) continue;
    if (bar.close >= bar.open) {
      bins[idx].buyVolume += bar.volume;
    } else {
      bins[idx].sellVolume += bar.volume;
    }
  }

  return bins;
}

class VolumeProfileRenderer implements IPrimitivePaneRenderer {
  private _bins: PriceBin[];
  private _chart: IChartApiBase<Time> | null;
  private _series: ISeriesApi<SeriesType, Time> | null;

  constructor(
    bins: PriceBin[],
    chart: IChartApiBase<Time> | null,
    series: ISeriesApi<SeriesType, Time> | null,
  ) {
    this._bins = bins;
    this._chart = chart;
    this._series = series;
  }

  draw(target: CanvasRenderingTarget2D): void {
    if (!this._chart || !this._series || this._bins.length === 0) return;

    const series = this._series;

    target.useBitmapCoordinateSpace((scope) => {
      const ctx = scope.context;
      const hRatio = scope.horizontalPixelRatio;
      const vRatio = scope.verticalPixelRatio;
      const chartWidth = scope.bitmapSize.width;
      const maxBarWidth = chartWidth * MAX_BAR_WIDTH_PCT;

      let maxVol = 0;
      for (const bin of this._bins) {
        const total = bin.buyVolume + bin.sellVolume;
        if (total > maxVol) maxVol = total;
      }
      if (maxVol === 0) return;

      const binHeight =
        this._bins.length >= 2
          ? Math.abs(
              ((series.priceToCoordinate(this._bins[1].price) ?? 0) -
                (series.priceToCoordinate(this._bins[0].price) ?? 0)) *
                vRatio,
            )
          : 4 * vRatio;

      const barH = Math.max(binHeight * 0.85, 1);

      for (const bin of this._bins) {
        const yCoord = series.priceToCoordinate(bin.price);
        if (yCoord === null) continue;

        const yCenter = yCoord * vRatio;
        const yTop = yCenter - barH / 2;
        const total = bin.buyVolume + bin.sellVolume;
        const totalWidth = (total / maxVol) * maxBarWidth;

        const buyWidth =
          total > 0 ? (bin.buyVolume / total) * totalWidth : 0;
        const sellWidth = totalWidth - buyWidth;

        const xRight = chartWidth - 2 * hRatio;

        if (sellWidth > 0) {
          ctx.fillStyle = SELL_COLOR;
          ctx.fillRect(xRight - totalWidth, yTop, sellWidth, barH);
        }
        if (buyWidth > 0) {
          ctx.fillStyle = BUY_COLOR;
          ctx.fillRect(xRight - buyWidth, yTop, buyWidth, barH);
        }
      }
    });
  }

  drawBackground(_target: CanvasRenderingTarget2D): void {}
}

class VolumeProfilePaneView implements IPrimitivePaneView {
  private _renderer: VolumeProfileRenderer;

  constructor(renderer: VolumeProfileRenderer) {
    this._renderer = renderer;
  }

  zOrder(): PrimitivePaneViewZOrder {
    return "top";
  }

  renderer(): IPrimitivePaneRenderer {
    return this._renderer;
  }
}

export class VolumeProfilePlugin implements ISeriesPrimitive<Time> {
  private _bars: VolumeBar[] = [];
  private _chart: IChartApiBase<Time> | null = null;
  private _series: ISeriesApi<SeriesType, Time> | null = null;
  private _requestUpdate: (() => void) | null = null;
  private _paneViews: VolumeProfilePaneView[] = [];

  setData(bars: VolumeBar[]): void {
    this._bars = bars;
    this._rebuildViews();
    this._requestUpdate?.();
  }

  attached(param: SeriesAttachedParameter<Time>): void {
    this._chart = param.chart;
    this._series = param.series as ISeriesApi<SeriesType, Time>;
    this._requestUpdate = param.requestUpdate;
    this._rebuildViews();
    param.requestUpdate();
  }

  detached(): void {
    this._chart = null;
    this._series = null;
    this._requestUpdate = null;
  }

  updateAllViews(): void {
    this._rebuildViews();
  }

  paneViews(): readonly IPrimitivePaneView[] {
    return this._paneViews;
  }

  private _rebuildViews(): void {
    const bins = computeBins(this._bars);
    const renderer = new VolumeProfileRenderer(
      bins,
      this._chart,
      this._series,
    );
    this._paneViews = [new VolumeProfilePaneView(renderer)];
  }
}
