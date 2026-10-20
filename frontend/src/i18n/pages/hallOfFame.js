// Copy for the redesigned Hall of Fame ("Общий рейтинг") page.
export default {
  ru: {
    hallPage: {
      eyebrow: 'Зал славы BMRL',
      updating: 'Обновляю…',
      summary: 'Сводка рейтинга',
      scope: 'Зачёт',
      order: 'Порядок: очки, затем золото, серебро, бронза',
      orderRating: 'Порядок: RER, затем очки и медали',
      podium: {
        eyebrow: 'Подиум · {scope}',
        pilots: 'Лучшие пилоты',
        teams: 'Лучшие команды',
        leader: 'Лидер',
        gap: '{points} оч. до лидера',
        gapRer: '{points} RER до лидера',
        bestRer: 'Лучший RER',
        members: 'Состав: {count}',
        open: 'Открыть: {name}'
      },
      table: {
        eyebrow: 'Таблица · {scope}',
        pilots: 'Все пилоты в зачёте',
        teams: 'Все команды в зачёте',
        shown: 'Найдено {shown} из {total}',
        total: 'В зачёте: {total}',
        number: 'Номер',
        noTeam: 'Без команды'
      },
      medals: {
        gold: '1 место: {count}',
        silver: '2 место: {count}',
        bronze: '3 место: {count}'
      },
      emptyText: 'Очки начисляются за подиумы в завершённых гонках. Выберите другую игру или загляните после ближайшего этапа.',
      noMatchTitle: 'Никого не нашли',
      noMatchText: 'По запросу «{query}» совпадений нет. Проверьте написание или сбросьте поиск.',
      resetSearch: 'Сбросить поиск',
      clearSearch: 'Очистить поиск'
    }
  },
  en: {
    hallPage: {
      eyebrow: 'BMRL Hall of Fame',
      updating: 'Updating…',
      summary: 'Rating summary',
      scope: 'Standings',
      order: 'Order: points, then gold, silver, bronze',
      orderRating: 'Order: RER, then points and medals',
      podium: {
        eyebrow: 'Podium · {scope}',
        pilots: 'Top pilots',
        teams: 'Top teams',
        leader: 'Leader',
        gap: '{points} pts behind the leader',
        gapRer: '{points} RER behind the leader',
        bestRer: 'Best RER',
        members: 'Roster: {count}',
        open: 'Open: {name}'
      },
      table: {
        eyebrow: 'Standings · {scope}',
        pilots: 'All rated pilots',
        teams: 'All rated teams',
        shown: '{shown} of {total} found',
        total: 'Rated: {total}',
        number: 'Number',
        noTeam: 'No team'
      },
      medals: {
        gold: '1st place: {count}',
        silver: '2nd place: {count}',
        bronze: '3rd place: {count}'
      },
      emptyText: 'Points come from podiums in finished races. Pick another game or check back after the next round.',
      noMatchTitle: 'Nobody found',
      noMatchText: 'Nothing matches “{query}”. Check the spelling or reset the search.',
      resetSearch: 'Reset search',
      clearSearch: 'Clear search'
    }
  }
}
