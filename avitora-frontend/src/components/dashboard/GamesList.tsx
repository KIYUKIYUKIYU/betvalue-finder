import type { TodaysGamesResponse } from '@/types/api';
import { format } from 'date-fns';
import { Card } from '@/components/ui/Card';

interface GamesListProps {
  data: TodaysGamesResponse;
}

export function GamesList({ data }: GamesListProps) {
  if (data.games.length === 0) {
    return (
      <Card>
        <div className="text-center py-gap-xl text-muted">
          今日の試合データがありません
        </div>
      </Card>
    );
  }

  const groupedBySport: Record<string, typeof data.games> = {};
  data.games.forEach((game) => {
    if (!groupedBySport[game.sport]) {
      groupedBySport[game.sport] = [];
    }
    groupedBySport[game.sport].push(game);
  });

  return (
    <div className="space-y-gap-md">
      {Object.entries(groupedBySport).map(([sport, games]) => (
        <Card key={sport} title={sport.toUpperCase()} subtitle={`${games.length}試合`}>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-gap-md">
            {games.map((game, index) => (
              <div
                key={index}
                className="p-gap-md rounded-lg border border-gray-200 hover:border-primary-500 transition-colors"
              >
                <div className="flex items-center justify-between mb-gap-xs">
                  <div className="font-medium text-gray-900">
                    {game.home_team} vs {game.away_team}
                  </div>
                  <div className="text-sm text-muted">
                    {format(new Date(game.commence_time), 'HH:mm')}
                  </div>
                </div>
                <div className="grid grid-cols-3 gap-gap-sm text-sm">
                  <div>
                    <div className="text-muted">ホーム</div>
                    <div className="font-medium text-gray-900">
                      {game.home_odds?.toFixed(2) || '—'}
                    </div>
                  </div>
                  <div>
                    <div className="text-muted">ドロー</div>
                    <div className="font-medium text-gray-900">
                      {game.draw_odds?.toFixed(2) || '—'}
                    </div>
                  </div>
                  <div>
                    <div className="text-muted">アウェイ</div>
                    <div className="font-medium text-gray-900">
                      {game.away_odds?.toFixed(2) || '—'}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Card>
      ))}
    </div>
  );
}
