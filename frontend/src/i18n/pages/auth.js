export default {
  ru: {
    authPage: {
      login: {
        eyebrow: 'Вход',
        title: 'С возвращением на трассу',
        lead: 'Войдите, чтобы записываться на гонки и следить за рейтингом и лицензией.',
        loginLabel: 'Логин или email',
        loginHint: 'Подойдёт любой из двух — тот, что вы указали при регистрации.',
        passwordLabel: 'Пароль',
        show: 'Показать пароль',
        hide: 'Скрыть пароль',
        submit: 'Войти',
        submitting: 'Входим…',
        or: 'или',
        steam: 'Войти через Steam',
        steamHint: 'Для аккаунта, привязанного к Steam, пароль не нужен.',
        noAccount: 'Ещё нет аккаунта?',
        register: 'Зарегистрироваться',
        registered: 'Аккаунт создан. Войдите — после одобрения модератором откроется запись на гонки.',
        asideTitle: 'Ваш номер ждёт',
        asideText: 'Профиль хранит рейтинг RER, лицензию, лучшие круги и историю заездов.'
      },
      register: {
        eyebrow: 'Регистрация пилота',
        title: 'Новый пилот',
        lead: 'Четыре коротких шага. Поля со звёздочкой обязательны.',
        optional: 'необязательно',
        steps: {
          steam: { title: 'Steam', text: 'Подтверждение' },
          account: { title: 'Аккаунт', text: 'Вход на сайт' },
          pilot: { title: 'Пилот', text: 'Как вас видят' },
          extra: { title: 'Симуляторы', text: 'Игры и связь' }
        },
        stepOf: 'Шаг {current} из {total}',
        steam: {
          title: 'Подтвердите Steam',
          text: 'Steam подтверждает, что за аккаунтом стоит реальный пилот, и связывает вас с результатами из симуляторов. Сайт получает только ваш Steam ID — пароль от Steam никуда не передаётся.',
          rule: 'Один Steam-аккаунт — один пилот.',
          connect: 'Подключить Steam',
          reconnect: 'Подключить заново',
          connected: 'Steam подключён',
          connectedHint: 'Подтверждение действует 15 минут — завершите регистрацию за это время.',
          missing: 'Steam ещё не подключён'
        },
        account: {
          title: 'Данные для входа',
          text: 'С ними вы будете входить на сайт.',
          loginHint: 'Нужен для входа на сайт. От 3 до 50 символов.',
          emailHint: 'Для важных сообщений от лиги. Другие пилоты его не видят.',
          passwordHint: 'Минимум 8 символов. Надёжнее — буквы разного регистра и цифры.',
          confirmHint: 'Повторите пароль, чтобы не ошибиться.',
          strength: ['Слабый пароль', 'Нормальный пароль', 'Надёжный пароль']
        },
        pilot: {
          title: 'Как вас увидят на трассе',
          text: 'Эти данные показываются в заявках, результатах и рейтинге.',
          firstNameHint: 'Как в протоколах гонок.',
          lastNameHint: 'Как в протоколах гонок.',
          nicknameHint: 'Ваш позывной в списках пилотов и рядом с именем.',
          numberHint: 'Постоянный номер на машине, от 0 до 999. Короткий дополнится нулями: 7 → 007.'
        },
        extra: {
          title: 'Симуляторы и связь',
          text: 'Почти готово — осталось выбрать игры.',
          gamesHint: 'Где вы гоняете. По этому списку работает фильтр «Только мои игры».',
          countryHint: 'Показывается в профиле и списке пилотов.',
          discordHint: 'Чтобы судьи и организаторы могли с вами связаться.'
        },
        next: 'Далее',
        back: 'Назад',
        submit: 'Создать аккаунт',
        submitting: 'Создаю аккаунт…',
        haveAccount: 'Уже есть аккаунт?',
        loginLink: 'Войти',
        errors: {
          required: 'Заполните это поле',
          loginLength: 'От 3 до 50 символов',
          email: 'Проверьте адрес: нужны @ и домен, например name@mail.ru',
          passwordLength: 'Минимум 8 символов',
          passwordMatch: 'Пароли не совпадают',
          number: 'Три цифры от 000 до 999',
          games: 'Выберите хотя бы один симулятор',
          steam: 'Сначала подключите Steam',
          terms: 'Без принятия соглашения аккаунт создать нельзя',
          consent: 'Без согласия на обработку данных аккаунт создать нельзя'
        },
        consents: {
          legend: 'Согласия',
          terms: { before: 'Принимаю', link: 'Пользовательское соглашение', after: '.' },
          privacy: { before: 'Даю согласие на обработку персональных данных по', link: 'Политике обработки персональных данных', after: '.' }
        },
        ok: {
          passwordMatch: 'Пароли совпадают',
          email: 'Адрес выглядит верно'
        },
        preview: {
          eyebrow: 'Лицензия пилота · предпросмотр',
          name: 'Имя Фамилия',
          nickname: 'позывной',
          steamOk: 'Steam подтверждён',
          steamMissing: 'Steam не подключён',
          number: 'Номер'
        },
        after: {
          title: 'Что будет дальше',
          items: [
            'Аккаунт создаётся со статусом «На рассмотрении».',
            'Модератор проверит данные и одобрит аккаунт.',
            'После одобрения откроется запись на гонки и чемпионаты.'
          ]
        }
      },
      serverErrors: {
        invalidCredentials: 'Неверный логин или пароль. Проверьте раскладку и Caps Lock.',
        duplicate: 'Этот логин, email или Steam-аккаунт уже зарегистрирован. Проверьте данные или войдите в существующий аккаунт. Steam нужно подключить заново.',
        steamRequired: 'Подтверждение Steam истекло или уже использовано. Подключите Steam ещё раз.',
        steamCancelled: 'Вход через Steam отменён.',
        steamFailed: 'Steam не подтвердил вход. Попробуйте ещё раз.',
        steamLinked: 'Этот Steam-аккаунт уже привязан к другому пилоту. Войдите в него.',
        steamNotLinked: 'Этот Steam-аккаунт не привязан ни к одному пилоту. Сначала зарегистрируйтесь.',
        storage: 'Сервис подтверждения Steam временно недоступен. Попробуйте позже.',
        accountStatus: 'Вход недоступен: статус аккаунта — {status}.'
      }
    }
  },
  en: {
    authPage: {
      login: {
        eyebrow: 'Sign in',
        title: 'Welcome back to the track',
        lead: 'Sign in to enter races and follow your rating and licence.',
        loginLabel: 'Login or email',
        loginHint: 'Either one works — the one you used to register.',
        passwordLabel: 'Password',
        show: 'Show password',
        hide: 'Hide password',
        submit: 'Sign in',
        submitting: 'Signing in…',
        or: 'or',
        steam: 'Sign in with Steam',
        steamHint: 'Accounts linked to Steam need no password.',
        noAccount: 'No account yet?',
        register: 'Sign up',
        registered: 'Account created. Sign in — race entry opens once a moderator approves it.',
        asideTitle: 'Your number is waiting',
        asideText: 'Your profile keeps your RER rating, licence, best laps and race history.'
      },
      register: {
        eyebrow: 'Pilot registration',
        title: 'New pilot',
        lead: 'Four short steps. Fields marked with an asterisk are required.',
        optional: 'optional',
        steps: {
          steam: { title: 'Steam', text: 'Verification' },
          account: { title: 'Account', text: 'Signing in' },
          pilot: { title: 'Pilot', text: 'How others see you' },
          extra: { title: 'Simulators', text: 'Games and contact' }
        },
        stepOf: 'Step {current} of {total}',
        steam: {
          title: 'Verify Steam',
          text: 'Steam proves a real pilot is behind the account and links you to simulator results. The site only receives your Steam ID — your Steam password never leaves Steam.',
          rule: 'One Steam account — one pilot.',
          connect: 'Connect Steam',
          reconnect: 'Connect again',
          connected: 'Steam connected',
          connectedHint: 'Verification lasts 15 minutes — finish registering within that time.',
          missing: 'Steam is not connected yet'
        },
        account: {
          title: 'Sign-in details',
          text: 'You will use these to sign in.',
          loginHint: 'Used to sign in. 3 to 50 characters.',
          emailHint: 'For important league messages. Other pilots never see it.',
          passwordHint: 'At least 8 characters. Mixed case and digits are stronger.',
          confirmHint: 'Repeat the password to avoid typos.',
          strength: ['Weak password', 'Fair password', 'Strong password']
        },
        pilot: {
          title: 'How you appear on track',
          text: 'Shown in entry lists, results and the rating.',
          firstNameHint: 'As in race reports.',
          lastNameHint: 'As in race reports.',
          nicknameHint: 'Your call sign in pilot lists and next to your name.',
          numberHint: 'Your permanent car number, 0 to 999. Short numbers get leading zeros: 7 → 007.'
        },
        extra: {
          title: 'Simulators and contact',
          text: 'Almost done — pick your games.',
          gamesHint: 'Where you race. The “My games only” filter uses this list.',
          countryHint: 'Shown on your profile and in the pilot list.',
          discordHint: 'So stewards and organisers can reach you.'
        },
        next: 'Next',
        back: 'Back',
        submit: 'Create account',
        submitting: 'Creating account…',
        haveAccount: 'Already have an account?',
        loginLink: 'Sign in',
        errors: {
          required: 'Fill in this field',
          loginLength: '3 to 50 characters',
          email: 'Check the address: it needs @ and a domain, e.g. name@mail.com',
          passwordLength: 'At least 8 characters',
          passwordMatch: 'Passwords do not match',
          number: 'Three digits from 000 to 999',
          games: 'Choose at least one simulator',
          steam: 'Connect Steam first',
          terms: 'An account cannot be created without accepting the agreement',
          consent: 'An account cannot be created without consent to data processing'
        },
        consents: {
          legend: 'Consents',
          terms: { before: 'I accept the', link: 'User Agreement', after: '.' },
          privacy: { before: 'I consent to the processing of my personal data under the', link: 'Personal Data Processing Policy', after: '.' }
        },
        ok: {
          passwordMatch: 'Passwords match',
          email: 'Address looks right'
        },
        preview: {
          eyebrow: 'Pilot licence · preview',
          name: 'First Last',
          nickname: 'call sign',
          steamOk: 'Steam verified',
          steamMissing: 'Steam not connected',
          number: 'Number'
        },
        after: {
          title: 'What happens next',
          items: [
            'The account is created with the “Under review” status.',
            'A moderator checks the details and approves the account.',
            'After approval you can enter races and championships.'
          ]
        }
      },
      serverErrors: {
        invalidCredentials: 'Wrong login or password. Check your keyboard layout and Caps Lock.',
        duplicate: 'This login, email or Steam account is already registered. Check the details or sign in to the existing account. Connect Steam again.',
        steamRequired: 'Steam verification expired or was already used. Connect Steam again.',
        steamCancelled: 'Steam sign-in was cancelled.',
        steamFailed: 'Steam did not confirm the sign-in. Try again.',
        steamLinked: 'This Steam account already belongs to another pilot. Sign in to it.',
        steamNotLinked: 'This Steam account is not linked to any pilot. Register first.',
        storage: 'Steam verification is temporarily unavailable. Try again later.',
        accountStatus: 'Sign-in is unavailable: account status is {status}.'
      }
    }
  }
}
