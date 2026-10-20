// Copy for the redesigned Teams page (/teams). Existing `teams.*` keys in
// messages.js are reused where they fit; everything new lives in `teamsPage`.
export default {
  ru: {
    teamsPage: {
      eyebrow: 'Паддок BMRL',
      lead: 'Составы, средний рейтинг и свободные места всех команд лиги. Откройте карточку, чтобы подать заявку или управлять своей командой.',
      stats: {
        label: 'Команды в цифрах',
        teams: 'Команд',
        pilots: 'Пилотов в составах',
        seats: 'Свободных мест'
      },
      limitChip: 'До {limit} пилотов в составе',
      myTeam: 'Моя команда',
      search: {
        label: 'Поиск команды',
        submit: 'Найти',
        reset: 'Сбросить поиск'
      },
      guest: {
        text: 'Войдите в аккаунт, чтобы подать заявку в команду или создать свою.',
        login: 'Войти'
      },
      emptySearch: {
        title: 'Ничего не нашлось',
        text: 'Попробуйте другое название, сокращение из трёх букв или слово из описания.'
      },
      empty: {
        text: 'Соберите первую команду лиги — заявку рассмотрит модератор.'
      },
      loadingTeam: 'Открываю команду…',
      dismiss: 'Скрыть сообщение',
      card: {
        open: 'Открыть команду {name}',
        rating: 'Средний RER',
        roster: 'Состав',
        full: 'Мест нет',
        mine: 'Ваша команда',
        owner: 'Вы владелец'
      },
      detail: {
        back: 'Все команды',
        switcher: 'Быстрый переход к другой команде'
      },
      hero: {
        averageSr: 'Средний SR',
        seatsLeft: 'Свободно мест: {count}',
        login: 'Войти и вступить'
      },
      roster: {
        eyebrow: 'Состав · {count} из {limit}',
        ratingGame: 'Рейтинг по симулятору',
        noMatchesText: 'Поиск идёт по имени, нику, логину и номеру пилота.'
      },
      manage: {
        eyebrow: 'Управление',
        hint: 'Этот блок видят только владелец команды и модераторы лиги.',
        tabRequests: 'Заявки',
        tabCard: 'Карточка',
        tabOwnership: 'Владение',
        requestsHint: 'Пилоты, которые хотят в состав. После одобрения пилот сразу появится в команде.',
        requestsEmpty: 'Когда пилот подаст заявку, она появится здесь, а на карточке команды загорится колокольчик.',
        preview: 'Так команду увидят в списке',
        pickFile: 'Выбрать файл',
        noFile: 'Файл не выбран',
        transferHint: 'Права перейдут выбранному участнику. Текущий владелец останется в составе.',
        dangerTitle: 'Удаление команды',
        dangerText: 'Команда исчезнет из списка, все участники останутся без команды. Отменить удаление нельзя.'
      },
      form: {
        nameHint: 'Полное название — его видят в списке команд и в заявках на гонки.',
        abbreviationHint: 'Ровно три латинские буквы, например NLR. Показывается в таблицах и протоколах.',
        colorHint: 'Фон аватарки и цвет ливреи на карточке команды.',
        customColor: 'Свой цвет',
        descriptionHint: 'Пара предложений: стиль, цели, кого ищете в состав.',
        optional: 'необязательно'
      },
      create: {
        eyebrow: 'Заявка модератору',
        preview: 'Предпросмотр карточки',
        cancel: 'Отмена'
      },
      requests: {
        eyebrow: 'Модерация'
      }
    }
  },
  en: {
    teamsPage: {
      eyebrow: 'BMRL paddock',
      lead: 'Rosters, average rating and open seats for every team in the league. Open a card to apply or to run your own team.',
      stats: {
        label: 'Teams at a glance',
        teams: 'Teams',
        pilots: 'Pilots on rosters',
        seats: 'Open seats'
      },
      limitChip: 'Up to {limit} pilots per roster',
      myTeam: 'My team',
      search: {
        label: 'Find a team',
        submit: 'Search',
        reset: 'Clear search'
      },
      guest: {
        text: 'Sign in to apply to a team or create your own.',
        login: 'Sign in'
      },
      emptySearch: {
        title: 'Nothing found',
        text: 'Try another name, the three-letter abbreviation or a word from the description.'
      },
      empty: {
        text: 'Start the league’s first team — a moderator reviews the request.'
      },
      loadingTeam: 'Opening the team…',
      dismiss: 'Dismiss message',
      card: {
        open: 'Open team {name}',
        rating: 'Avg RER',
        roster: 'Roster',
        full: 'Full',
        mine: 'Your team',
        owner: 'You own it'
      },
      detail: {
        back: 'All teams',
        switcher: 'Jump to another team'
      },
      hero: {
        averageSr: 'Avg SR',
        seatsLeft: 'Open seats: {count}',
        login: 'Sign in to join'
      },
      roster: {
        eyebrow: 'Roster · {count} of {limit}',
        ratingGame: 'Rating by simulator',
        noMatchesText: 'Search matches the pilot’s name, nickname, login and number.'
      },
      manage: {
        eyebrow: 'Management',
        hint: 'Only the team owner and league moderators can see this block.',
        tabRequests: 'Requests',
        tabCard: 'Team card',
        tabOwnership: 'Ownership',
        requestsHint: 'Pilots who want to join. Once approved, the pilot is added to the roster straight away.',
        requestsEmpty: 'New requests show up here, and a bell lights up on the team card.',
        preview: 'How the team looks in the list',
        pickFile: 'Choose file',
        noFile: 'No file chosen',
        transferHint: 'Ownership moves to the selected member. The current owner stays on the roster.',
        dangerTitle: 'Delete team',
        dangerText: 'The team disappears from the list and every member is left without a team. This cannot be undone.'
      },
      form: {
        nameHint: 'Full name, shown in the team list and on race entries.',
        abbreviationHint: 'Exactly three latin letters, e.g. NLR. Used in tables and results.',
        colorHint: 'Avatar background and the livery colour on the team card.',
        customColor: 'Custom colour',
        descriptionHint: 'A couple of sentences: style, goals, who you are looking for.',
        optional: 'optional'
      },
      create: {
        eyebrow: 'Request to moderators',
        preview: 'Card preview',
        cancel: 'Cancel'
      },
      requests: {
        eyebrow: 'Moderation'
      }
    }
  }
}
