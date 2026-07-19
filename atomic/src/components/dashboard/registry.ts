import type { FC } from 'react';
import { BriefingWidget } from './widgets/BriefingWidget';
import { ActivityWidget } from './widgets/ActivityWidget';
import { NewWikisWidget } from './widgets/NewWikisWidget';
import { RevisionsWidget } from './widgets/RevisionsWidget';

export type WidgetSpan = 'full' | 'half';

export interface DashboardWidget {
  id: string;
  span: WidgetSpan;
  Component: FC;
}

export const dashboardWidgets: DashboardWidget[] = [
  { id: 'briefing', span: 'full', Component: BriefingWidget },
  { id: 'activity', span: 'half', Component: ActivityWidget },
  { id: 'new-wikis', span: 'half', Component: NewWikisWidget },
  { id: 'revisions', span: 'full', Component: RevisionsWidget },
];
