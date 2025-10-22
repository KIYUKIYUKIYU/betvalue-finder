import type { TodaysGamesResponse } from '@/types/api';
import { format } from 'date-fns';
import { Card } from '@/components/ui/Card';

interface GamesListProps {
  data: TodaysGamesResponse;
}

export function GamesList({ data }: GamesListProps) {
  // Check if all sports have no games
  const totalGames =
    data.games.mlb.length +
    data.games.npb.length +
    data.games.soccer.length +
    data.games.nba.length;

  if (totalGames === 0) {
    return (
      <Card>
        <div className="text-center py-gap-xl text-muted">
          今日の試合データがありません
        </div>
      </Card>
    );
  }

  const sportLabels: Record<string, string> = {
    mlb: 'MLB',
    npb: 'NPB',
    soccer: 'サッカー',
    nba: 'NBA',
  };

  return (
    <div className="space-y-gap-md">
      {Object.entries(data.games).map(([sport, games]) => {
        if (games.length === 0) return null;

        return (
          <Card key={sport} title={sportLabels[sport]} subtitle={`${games.length}試合`}>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-gap-md">
              {games.map((game) => (
                <div
                  key={game.id}
                  className="p-gap-md rounded-lg border border-gray-200 hover:border-primary-500 transition-colors"
                >
                  <div className="flex items-center justify-between mb-gap-xs">
                    <div className="font-medium text-gray-900">
                      {game.home_team_jp} vs {game.away_team_jp}
                    </div>
                    <div className="text-sm text-muted">
                      {game.start_time_display || format(new Date(game.start_time_jst), 'HH:mm')}
                    </div>
                  </div>
                  {game.league_jp && (
                    <div className="text-xs text-muted mt-gap-xs">
                      {game.league_jp}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </Card>
        );
      })}
    </div>
  );
}
