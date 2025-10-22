import type { GameEvaluation } from '@/types/api';
import { format } from 'date-fns';

interface AnalysisResultProps {
  results: GameEvaluation[];
}

export function AnalysisResult({ results }: AnalysisResultProps) {
  if (results.length === 0) {
    return (
      <div className="text-center py-gap-xl text-muted">
        分析結果がここに表示されます
      </div>
    );
  }

  const formatValue = (value: number | null): string => {
    if (value === null) return '—';
    return value.toFixed(2);
  };

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="bg-gray-100">
          <tr>
            <th className="px-gap-md py-gap-sm text-left font-medium text-gray-900">試合</th>
            <th className="px-gap-md py-gap-sm text-left font-medium text-gray-900">日時</th>
            <th className="px-gap-md py-gap-sm text-left font-medium text-gray-900">チーム</th>
            <th className="px-gap-md py-gap-sm text-right font-medium text-gray-900">Pinnacleオッズ</th>
            <th className="px-gap-md py-gap-sm text-right font-medium text-gray-900">フェアオッズ</th>
            <th className="px-gap-md py-gap-sm text-right font-medium text-gray-900">EV%</th>
            <th className="px-gap-md py-gap-sm text-right font-medium text-gray-900">評価</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200">
          {results.map((result, index) => {
            if (result.error) {
              return (
                <tr key={index} className="hover:bg-gray-50">
                  <td colSpan={7} className="px-gap-md py-gap-sm text-danger-600">
                    エラー: {result.error}
                  </td>
                </tr>
              );
            }

            const homeEV = result.home_team_odds?.ev_percentage;
            const awayEV = result.away_team_odds?.ev_percentage;
            const homeVerdict = result.home_team_odds?.verdict;
            const awayVerdict = result.away_team_odds?.verdict;

            return (
              <>
                <tr key={`${index}-home`} className="hover:bg-gray-50">
                  <td className="px-gap-md py-gap-sm" rowSpan={2}>
                    <div className="font-medium text-gray-900">
                      {result.home_team_jp || '—'} vs {result.away_team_jp || '—'}
                    </div>
                    <div className="text-xs text-muted">{result.sport || '—'}</div>
                  </td>
                  <td className="px-gap-md py-gap-sm text-muted" rowSpan={2}>
                    {result.game_date ? format(new Date(result.game_date), 'MM/dd HH:mm') : '—'}
                  </td>
                  <td className="px-gap-md py-gap-sm">
                    <span className="text-gray-900">ホーム: {result.home_team_jp || '—'}</span>
                  </td>
                  <td className="px-gap-md py-gap-sm text-right text-gray-900">
                    {formatValue(result.home_team_odds?.raw_pinnacle_odds)}
                  </td>
                  <td className="px-gap-md py-gap-sm text-right text-gray-900">
                    {formatValue(result.home_team_odds?.fair_odds)}
                  </td>
                  <td className="px-gap-md py-gap-sm text-right">
                    <span className={homeEV && homeEV > 0 ? 'text-success-600 font-medium' : 'text-gray-900'}>
                      {homeEV !== null && homeEV !== undefined ? `${homeEV.toFixed(2)}%` : '—'}
                    </span>
                  </td>
                  <td className="px-gap-md py-gap-sm text-right">
                    {homeVerdict === 'BET' && (
                      <span className="inline-flex items-center px-gap-sm py-gap-xs rounded-full text-xs font-medium bg-success-600 bg-opacity-10 text-success-600">
                        推奨
                      </span>
                    )}
                    {homeVerdict === 'SKIP' && (
                      <span className="inline-flex items-center px-gap-sm py-gap-xs rounded-full text-xs font-medium bg-gray-100 text-muted">
                        スキップ
                      </span>
                    )}
                    {homeVerdict === 'CLOSE' && (
                      <span className="inline-flex items-center px-gap-sm py-gap-xs rounded-full text-xs font-medium bg-warning-600 bg-opacity-10 text-warning-600">
                        微妙
                      </span>
                    )}
                  </td>
                </tr>
                <tr key={`${index}-away`} className="hover:bg-gray-50">
                  <td className="px-gap-md py-gap-sm">
                    <span className="text-gray-900">アウェイ: {result.away_team_jp || '—'}</span>
                  </td>
                  <td className="px-gap-md py-gap-sm text-right text-gray-900">
                    {formatValue(result.away_team_odds?.raw_pinnacle_odds)}
                  </td>
                  <td className="px-gap-md py-gap-sm text-right text-gray-900">
                    {formatValue(result.away_team_odds?.fair_odds)}
                  </td>
                  <td className="px-gap-md py-gap-sm text-right">
                    <span className={awayEV && awayEV > 0 ? 'text-success-600 font-medium' : 'text-gray-900'}>
                      {awayEV !== null && awayEV !== undefined ? `${awayEV.toFixed(2)}%` : '—'}
                    </span>
                  </td>
                  <td className="px-gap-md py-gap-sm text-right">
                    {awayVerdict === 'BET' && (
                      <span className="inline-flex items-center px-gap-sm py-gap-xs rounded-full text-xs font-medium bg-success-600 bg-opacity-10 text-success-600">
                        推奨
                      </span>
                    )}
                    {awayVerdict === 'SKIP' && (
                      <span className="inline-flex items-center px-gap-sm py-gap-xs rounded-full text-xs font-medium bg-gray-100 text-muted">
                        スキップ
                      </span>
                    )}
                    {awayVerdict === 'CLOSE' && (
                      <span className="inline-flex items-center px-gap-sm py-gap-xs rounded-full text-xs font-medium bg-warning-600 bg-opacity-10 text-warning-600">
                        微妙
                      </span>
                    )}
                  </td>
                </tr>
              </>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
