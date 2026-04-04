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

export interface BandPoint {
  time: Time;
  upper: number;
  lower: number;
}

class BollingerFillRenderer implements IPrimitivePaneRenderer {
  private _data: BandPoint[];
  private _fillColor: string;
  private _chart: IChartApiBase<Time> | null;
  private _series: ISeriesApi<SeriesType, Time> | null;

  constructor(
    data: BandPoint[],
    fillColor: string,
    chart: IChartApiBase<Time> | null,
    series: ISeriesApi<SeriesType, Time> | null,
  ) {
    this._data = data;
    this._fillColor = fillColor;
    this._chart = chart;
    this._series = series;
  }

  draw(_target: CanvasRenderingTarget2D): void {}

  drawBackground(target: CanvasRenderingTarget2D): void {
    if (!this._chart || !this._series || this._data.length === 0) return;

    const timeScale = this._chart.timeScale();
    const series = this._series;

    target.useBitmapCoordinateSpace((scope) => {
      const ctx = scope.context;
      const hRatio = scope.horizontalPixelRatio;
      const vRatio = scope.verticalPixelRatio;

      const upperPoints: { x: number; y: number }[] = [];
      const lowerPoints: { x: number; y: number }[] = [];

      for (const point of this._data) {
        const xMedia = timeScale.timeToCoordinate(point.time);
        const yUpper = series.priceToCoordinate(point.upper);
        const yLower = series.priceToCoordinate(point.lower);

        if (xMedia === null || yUpper === null || yLower === null) continue;

        upperPoints.push({ x: xMedia * hRatio, y: yUpper * vRatio });
        lowerPoints.push({ x: xMedia * hRatio, y: yLower * vRatio });
      }

      if (upperPoints.length < 2) return;

      const path = new Path2D();
      path.moveTo(upperPoints[0].x, upperPoints[0].y);
      for (let i = 1; i < upperPoints.length; i++) {
        path.lineTo(upperPoints[i].x, upperPoints[i].y);
      }
      for (let i = lowerPoints.length - 1; i >= 0; i--) {
        path.lineTo(lowerPoints[i].x, lowerPoints[i].y);
      }
      path.closePath();

      ctx.fillStyle = this._fillColor;
      ctx.fill(path);
    });
  }
}

class BollingerFillPaneView implements IPrimitivePaneView {
  private _renderer: BollingerFillRenderer;

  constructor(renderer: BollingerFillRenderer) {
    this._renderer = renderer;
  }

  zOrder(): PrimitivePaneViewZOrder {
    return "bottom";
  }

  renderer(): IPrimitivePaneRenderer {
    return this._renderer;
  }
}

export class BollingerFillPlugin implements ISeriesPrimitive<Time> {
  private _data: BandPoint[];
  private _fillColor: string;
  private _chart: IChartApiBase<Time> | null = null;
  private _series: ISeriesApi<SeriesType, Time> | null = null;
  private _requestUpdate: (() => void) | null = null;
  private _paneViews: BollingerFillPaneView[] = [];

  constructor(
    bandData: BandPoint[],
    fillColor: string = "rgba(0,212,255,0.08)",
  ) {
    this._data = bandData;
    this._fillColor = fillColor;
    this._rebuildViews();
  }

  setData(data: BandPoint[]): void {
    this._data = data;
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
    const renderer = new BollingerFillRenderer(
      this._data,
      this._fillColor,
      this._chart,
      this._series,
    );
    this._paneViews = [new BollingerFillPaneView(renderer)];
  }
}
