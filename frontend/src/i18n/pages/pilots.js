export default {
  ru: {
    pilotsPage: {
      eyebrow: 'Рейтинг RER',
      lead: 'Собственный рейтинг лиги — отдельный для каждого симулятора. Все начинают с 1000, максимум — 10 000. Рейтинг меняется только по итогам гонок: обогнать сильного соперника выгоднее, проиграть слабому — дороже.',
      tabs: {
        pilots: 'Пилоты',
        tracks: 'Трассы'
      },
      tiersTitle: 'Лицензии',
      yourTier: 'Ваша',
      searchPlaceholder: 'Имя, ник, номер или команда',
      columns: {
        place: '#',
        pilot: 'Пилот',
        team: 'Команда',
        country: 'Страна',
        rer: 'RER',
        sr: 'SR',
        races: 'Гонок'
      },
      noTeam: '—',
      emptyTitle: 'Пилоты не найдены',
      emptyText: 'Измените запрос или сбросьте поиск.',
      resetSearch: 'Сбросить поиск',
      tracks: {
        searchPlaceholder: 'Найти трассу',
        recordsTitle: 'Рекорды трассы',
        pickTrack: 'Выберите трассу, чтобы увидеть рекорды.',
        manageImage: 'Изображение трассы',
        mapAlt: 'Схема трассы {track}',
        layout: {
          badge: 'Есть 3D-схема с рекордами секторов',
          figure: '3D-схема трассы {track}',
          corner: 'Поворот',
          hint: 'Потяните, чтобы повернуть',
          stats: 'Рекорды трассы {track}',
          bestLap: 'Лучший круг',
          noLap: 'Лучшего круга пока нет.',
          sectors: 'Лучшие секторы',
          sectorHolder: 'Сектор {n}: {name}, {time}',
          sectorFree: 'Времени пока нет',
          noSectors: 'Времён секторов по этой трассе пока нет: они берутся из файлов результатов симулятора (ACC, Assetto Corsa).',
          ideal: 'Идеальный круг',
          idealNote: 'Сумма лучших секторов',
          gap: '{gap} к рекорду',
          counted: 'Учтено зачётных кругов: {laps} · пилотов: {pilots}'
        }
      }
    }
  },
  en: {
    pilotsPage: {
      eyebrow: 'RER rating',
      lead: 'The league’s own rating — separate for every simulator. Everyone starts at 1000, the maximum is 10,000. It changes only with race results: beating a stronger rival earns more, losing to a weaker one costs more.',
      tabs: {
        pilots: 'Pilots',
        tracks: 'Tracks'
      },
      tiersTitle: 'Licences',
      yourTier: 'Yours',
      searchPlaceholder: 'Name, nickname, number or team',
      columns: {
        place: '#',
        pilot: 'Pilot',
        team: 'Team',
        country: 'Country',
        rer: 'RER',
        sr: 'SR',
        races: 'Races'
      },
      noTeam: '—',
      emptyTitle: 'No pilots found',
      emptyText: 'Change the query or clear the search.',
      resetSearch: 'Clear search',
      tracks: {
        searchPlaceholder: 'Find a track',
        recordsTitle: 'Track records',
        pickTrack: 'Pick a track to see its records.',
        manageImage: 'Track image',
        mapAlt: 'Map of {track}',
        layout: {
          badge: 'Has a 3D layout with sector records',
          figure: '3D layout of {track}',
          corner: 'Turn',
          hint: 'Drag to turn it round',
          stats: 'Records of {track}',
          bestLap: 'Lap record',
          noLap: 'No lap record yet.',
          sectors: 'Best sectors',
          sectorHolder: 'Sector {n}: {name}, {time}',
          sectorFree: 'No time yet',
          noSectors: 'No sector times for this track yet: they come from the simulator’s result files (ACC, Assetto Corsa).',
          ideal: 'Ideal lap',
          idealNote: 'The best sectors put together',
          gap: '{gap} to the record',
          counted: 'Valid laps counted: {laps} · pilots: {pilots}'
        }
      }
    }
  }
}
