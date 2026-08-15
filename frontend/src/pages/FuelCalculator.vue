<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { Calculator, Fuel, Gauge, TimerReset } from 'lucide-vue-next'
import { api } from '../api'
import { state } from '../store'

const presets = {
  ACC: [
    { label: 'GT3', tank: 120, fuel: 3.2, hintRu: 'Проверь расход в MFD после серии боевых кругов.', hintEn: 'Check consumption in the MFD after a race-pace run.' },
    { label: 'GT2', tank: 120, fuel: 3.5, hintRu: 'GT2 мощнее GT3, поэтому стартовый расход выше.', hintEn: 'GT2 is more powerful than GT3, so the default burn is higher.' },
    { label: 'GT4', tank: 100, fuel: 2.6, hintRu: 'Для GT4 расход обычно ниже, но трасса сильно влияет.', hintEn: 'GT4 usually burns less fuel, but track layout matters.' },
    { label: 'TCX', tank: 65, fuel: 2.1, hintRu: 'Для TCX используй данные после нескольких кругов в боевом темпе.', hintEn: 'For TCX, use race-pace data after a few laps.' },
    { label: 'Ferrari Challenge', tank: 110, fuel: 3.0, hintRu: 'Для Challenge лучше брать запас не меньше одного круга.', hintEn: 'For Challenge races, keep at least one lap of reserve.' },
    { label: 'Lamborghini Super Trofeo', tank: 120, fuel: 3.2, hintRu: 'Super Trofeo близок по расходу к GT3/GTC, уточняй по MFD.', hintEn: 'Super Trofeo is close to GT3/GTC burn; verify in MFD.' },
    { label: 'Porsche CUP', tank: 100, fuel: 3.0, hintRu: 'Для Cup лучше брать запас не меньше одного круга.', hintEn: 'For Cup races, keep at least one lap of reserve.' }
  ],
  AC: [
    { label: 'GT', tank: 100, fuel: 3.1, hintRu: 'Для AC и модов проверь бак в настройках машины.', hintEn: 'For AC and mods, verify tank capacity in the car setup.' },
    { label: 'Touring', tank: 70, fuel: 2.4, hintRu: 'Для туринговых машин чаще хватает меньшего бака.', hintEn: 'Touring cars often need a smaller tank.' }
  ],
  iRacing: [
    { label: 'GT3', tank: 110, fuel: 3.1, hintRu: 'Бак и расход смотри в Garage -> Fuel.', hintEn: 'Check tank and consumption in Garage -> Fuel.' },
    { label: 'Prototype', tank: 75, fuel: 4.4, hintRu: 'Для прототипов расход выше, проверь race control calculator.', hintEn: 'Prototypes burn more fuel; cross-check race control calculator.' },
    { label: 'GT4', tank: 100, fuel: 2.6, hintRu: 'Для GT4 используй данные с гоночного темпа.', hintEn: 'For GT4, use race-pace fuel data.' },
    { label: 'Touring', tank: 65, fuel: 2.2, hintRu: 'Для туринга расход сильнее зависит от трассы.', hintEn: 'Touring fuel burn depends heavily on the track.' },
    { label: 'Cup', tank: 100, fuel: 3.0, hintRu: 'Для кубковых машин оставляй запас хотя бы на круг.', hintEn: 'For cup cars, keep at least one lap of reserve.' }
  ],
  LMU: [
    { label: 'Hypercar', tank: 70, fuel: 4.6, hintRu: 'Здесь считается обычное топливо, не Virtual Energy.', hintEn: 'This calculates fuel, not Virtual Energy.' },
    { label: 'LMP2', tank: 75, fuel: 3.9, hintRu: 'Для LMP2 проверяй расход на длинном отрезке.', hintEn: 'For LMP2, verify fuel burn over a longer run.' },
    { label: 'LMP3', tank: 70, fuel: 3.4, hintRu: 'Для LMP3 держи запас из-за трафика.', hintEn: 'For LMP3, keep reserve for traffic.' },
    { label: 'LMGT3', tank: 100, fuel: 3.4, hintRu: 'Для LMGT3 бери расход с боевого темпа.', hintEn: 'For LMGT3, use race-pace consumption.' },
    { label: 'GTE', tank: 100, fuel: 3.6, hintRu: 'Для GTE используй расход из нескольких боевых кругов.', hintEn: 'For GTE, use fuel burn from several race-pace laps.' }
  ]
}

const fuelCars = {
  ACC: [
    { label: 'Aston Martin V12 Vantage GT3 2013', class: 'GT3', tank: 132, fuel: 3.25 },
    { label: 'Aston Martin V8 Vantage GT3 2019', class: 'GT3', tank: 120, fuel: 3.15 },
    { label: 'Audi R8 LMS GT3 2015', class: 'GT3', tank: 120, fuel: 3.2 },
    { label: 'Audi R8 LMS Evo GT3 2019', class: 'GT3', tank: 120, fuel: 3.15 },
    { label: 'Audi R8 LMS Evo II GT3 2022', class: 'GT3', tank: 120, fuel: 3.15 },
    { label: 'Bentley Continental GT3 2015', class: 'GT3', tank: 132, fuel: 3.35 },
    { label: 'Bentley Continental GT3 2018', class: 'GT3', tank: 132, fuel: 3.35 },
    { label: 'BMW M6 GT3 2017', class: 'GT3', tank: 125, fuel: 3.25 },
    { label: 'BMW M4 GT3 2021', class: 'GT3', tank: 120, fuel: 3.15 },
    { label: 'Emil Frey Jaguar GT3 2012', class: 'GT3', tank: 119, fuel: 3.3 },
    { label: 'Ferrari 296 GT3 2023', class: 'GT3', tank: 110, fuel: 3.1 },
    { label: 'Ferrari 488 GT3 2018', class: 'GT3', tank: 110, fuel: 3.15 },
    { label: 'Ferrari 488 EVO GT3 2020', class: 'GT3', tank: 110, fuel: 3.1 },
    { label: 'Ford Mustang GT3 2024', class: 'GT3', tank: 120, fuel: 3.2 },
    { label: 'Honda NSX GT3 2017', class: 'GT3', tank: 120, fuel: 3.2 },
    { label: 'Honda NSX Evo GT3 2019', class: 'GT3', tank: 120, fuel: 3.15 },
    { label: 'Lamborghini Huracan EVO2 GT3 2023', class: 'GT3', tank: 120, fuel: 3.2 },
    { label: 'Lamborghini Huracan GT3 2015', class: 'GT3', tank: 120, fuel: 3.25 },
    { label: 'Lamborghini Huracan Evo GT3 2019', class: 'GT3', tank: 120, fuel: 3.2 },
    { label: 'Lexus RC F GT3 2016', class: 'GT3', tank: 120, fuel: 3.2 },
    { label: 'McLaren 650S GT3 2015', class: 'GT3', tank: 125, fuel: 3.2 },
    { label: 'McLaren 720S GT3 2019', class: 'GT3', tank: 125, fuel: 3.15 },
    { label: 'McLaren 720S Evo GT3 2023', class: 'GT3', tank: 125, fuel: 3.15 },
    { label: 'Mercedes AMG GT3 2015', class: 'GT3', tank: 120, fuel: 3.25 },
    { label: 'Mercedes AMG Evo GT3 2020', class: 'GT3', tank: 120, fuel: 3.2 },
    { label: 'Nissan GTR Nismo GT3 2015', class: 'GT3', tank: 132, fuel: 3.35 },
    { label: 'Nissan GTR Nismo GT3 2018', class: 'GT3', tank: 132, fuel: 3.35 },
    { label: 'Porsche 911 GT3 R 2018', class: 'GT3', tank: 120, fuel: 3.15 },
    { label: 'Porsche 911 II GT3R 2019', class: 'GT3', tank: 120, fuel: 3.15 },
    { label: 'Porsche 992 GT3R 2023', class: 'GT3', tank: 120, fuel: 3.15 },
    { label: 'Reiter Engineering R-EX GT3 2017', class: 'GT3', tank: 130, fuel: 3.35 },
    { label: 'Audi R8 LMS GT2', class: 'GT2', tank: 120, fuel: 3.5 },
    { label: 'KTM X-Bow GT2', class: 'GT2', tank: 120, fuel: 3.45 },
    { label: 'Maserati MC20 GT2', class: 'GT2', tank: 120, fuel: 3.5 },
    { label: 'Mercedes-AMG GT2', class: 'GT2', tank: 120, fuel: 3.55 },
    { label: 'Porsche 935 (2019)', class: 'GT2', tank: 120, fuel: 3.5 },
    { label: 'Porsche 911 GT2 RS CS EVO Kit', class: 'GT2', tank: 120, fuel: 3.5 },
    { label: 'Alpine A110 2018', class: 'GT4', tank: 80, fuel: 2.35 },
    { label: 'AMR V8 Vantage 2018', class: 'GT4', tank: 100, fuel: 2.65 },
    { label: 'Audi R8 LMS 2018', class: 'GT4', tank: 100, fuel: 2.65 },
    { label: 'BMW M4 2018', class: 'GT4', tank: 100, fuel: 2.65 },
    { label: 'Chevrolet Camaro R 2017', class: 'GT4', tank: 100, fuel: 2.8 },
    { label: 'Ginetta G55 2012', class: 'GT4', tank: 80, fuel: 2.4 },
    { label: 'KTM X-Bow 2016', class: 'GT4', tank: 100, fuel: 2.5 },
    { label: 'Maserati Granturismo MC 2016', class: 'GT4', tank: 100, fuel: 2.75 },
    { label: 'McLaren 570S 2016', class: 'GT4', tank: 100, fuel: 2.6 },
    { label: 'Mercedes AMG 2016', class: 'GT4', tank: 100, fuel: 2.7 },
    { label: 'Porsche 718 Cayman GT4 Clubsport 2019', class: 'GT4', tank: 100, fuel: 2.55 },
    { label: 'BMW M2 CS 2020', class: 'TCX', tank: 65, fuel: 2.1 },
    { label: 'Ferrari 488 Challenge Evo 2020', class: 'Ferrari Challenge', tank: 110, fuel: 3.0 },
    { label: 'Lamborghini Huracan Super Trofeo 2015', class: 'Lamborghini Super Trofeo', tank: 120, fuel: 3.2 },
    { label: 'Lamborghini Huracan Super Trofeo Evo 2 2021', class: 'Lamborghini Super Trofeo', tank: 120, fuel: 3.2 },
    { label: 'Porsche 911 II GT3 Cup 2017', class: 'Porsche CUP', tank: 100, fuel: 3.0 },
    { label: 'Porsche 911 GT3 Cup (992) 2021', class: 'Porsche CUP', tank: 100, fuel: 3.0 }
  ],
  AC: [
    { label: 'BMW M3 GT2', class: 'GT', tank: 100, fuel: 3.3 },
    { label: 'BMW Z4 GT3', class: 'GT', tank: 100, fuel: 3.1 },
    { label: 'Chevrolet Corvette C7.R', class: 'GT', tank: 100, fuel: 3.4 },
    { label: 'Ferrari 458 GT2', class: 'GT', tank: 100, fuel: 3.3 },
    { label: 'Ferrari 488 GT3', class: 'GT', tank: 110, fuel: 3.1 },
    { label: 'Lamborghini Huracan GT3', class: 'GT', tank: 120, fuel: 3.2 },
    { label: 'Maserati Granturismo MC GT4', class: 'GT', tank: 100, fuel: 2.7 },
    { label: 'McLaren 650S GT3', class: 'GT', tank: 125, fuel: 3.2 },
    { label: 'McLaren MP4-12C GT3', class: 'GT', tank: 100, fuel: 3.1 },
    { label: 'Mercedes-Benz AMG GT3', class: 'GT', tank: 120, fuel: 3.2 },
    { label: 'Nissan GT-R Nismo GT3', class: 'GT', tank: 120, fuel: 3.3 },
    { label: 'Porsche 911 GT3 Cup 2017', class: 'GT', tank: 100, fuel: 3.0 },
    { label: 'Porsche 911 GT3 R 2016', class: 'GT', tank: 120, fuel: 3.1 },
    { label: 'Porsche 911 RSR 2017', class: 'GT', tank: 100, fuel: 3.5 },
    { label: 'Porsche Cayman GT4 Clubsport', class: 'GT', tank: 100, fuel: 2.6 },
    { label: 'Audi TT Cup 2016', class: 'Touring', tank: 70, fuel: 2.3 },
    { label: 'BMW M235i Racing', class: 'Touring', tank: 65, fuel: 2.2 },
    { label: 'Mazda MX-5 Cup', class: 'Touring', tank: 50, fuel: 1.8 },
    { label: 'Audi R18 e-tron quattro', class: 'Prototype', tank: 90, fuel: 4.0 },
    { label: 'Ferrari 312T', class: 'Formula', tank: 180, fuel: 3.6 },
    { label: 'Ferrari F138', class: 'Formula', tank: 100, fuel: 2.5 },
    { label: 'Ferrari SF15-T', class: 'Formula', tank: 100, fuel: 2.5 },
    { label: 'Lotus Exos T125', class: 'Formula', tank: 100, fuel: 2.8 },
    { label: 'Lotus 98T', class: 'Formula', tank: 195, fuel: 4.0 },
    { label: 'Porsche 919 Hybrid 2015', class: 'Prototype', tank: 90, fuel: 4.0 },
    { label: 'Porsche 919 Hybrid 2016', class: 'Prototype', tank: 90, fuel: 4.0 }
  ],
  iRacing: [
    { label: 'Aston Martin GT3 EVO', class: 'GT3', tank: 120, fuel: 3.1 },
    { label: 'Acura NSX GT3 EVO 22', class: 'GT3', tank: 120, fuel: 3.1 },
    { label: 'Audi R8 LMS EVO II GT3', class: 'GT3', tank: 120, fuel: 3.1 },
    { label: 'BMW M4 GT3 EVO', class: 'GT3', tank: 120, fuel: 3.1 },
    { label: 'Chevrolet Corvette Z06 GT3.R', class: 'GT3', tank: 120, fuel: 3.1 },
    { label: 'Ferrari 296 GT3', class: 'GT3', tank: 110, fuel: 3.1 },
    { label: 'Ford Mustang GT3', class: 'GT3', tank: 120, fuel: 3.2 },
    { label: 'Lamborghini Huracan GT3 EVO', class: 'GT3', tank: 120, fuel: 3.2 },
    { label: 'McLaren 720S GT3 EVO', class: 'GT3', tank: 125, fuel: 3.1 },
    { label: 'Mercedes-AMG GT3 2020', class: 'GT3', tank: 120, fuel: 3.2 },
    { label: 'Porsche 911 GT3 R (992)', class: 'GT3', tank: 120, fuel: 3.1 },
    { label: 'Acura ARX-06 GTP', class: 'Prototype', tank: 75, fuel: 4.4 },
    { label: 'BMW M Hybrid V8', class: 'Prototype', tank: 75, fuel: 4.4 },
    { label: 'Cadillac V-Series.R GTP', class: 'Prototype', tank: 75, fuel: 4.4 },
    { label: 'Ferrari 499P', class: 'Prototype', tank: 75, fuel: 4.4 },
    { label: 'Porsche 963 GTP', class: 'Prototype', tank: 75, fuel: 4.4 },
    { label: 'Dallara P217', class: 'Prototype', tank: 75, fuel: 4.1 },
    { label: 'Ligier JS P320', class: 'Prototype', tank: 75, fuel: 3.8 },
    { label: 'Aston Martin Vantage GT4', class: 'GT4', tank: 100, fuel: 2.6 },
    { label: 'BMW M4 G82 GT4 Evo', class: 'GT4', tank: 100, fuel: 2.6 },
    { label: 'Ford Mustang GT4', class: 'GT4', tank: 100, fuel: 2.7 },
    { label: 'Porsche 718 Cayman GT4 Clubsport MR', class: 'GT4', tank: 100, fuel: 2.55 },
    { label: 'McLaren 570S GT4', class: 'GT4', tank: 100, fuel: 2.6 },
    { label: 'Mercedes-AMG GT4', class: 'GT4', tank: 100, fuel: 2.65 },
    { label: 'BMW M2 Racing (G87)', class: 'Touring', tank: 65, fuel: 2.2 },
    { label: 'BMW M2 CS Racing', class: 'Touring', tank: 65, fuel: 2.2 },
    { label: 'Toyota GR86', class: 'Touring', tank: 50, fuel: 1.8 },
    { label: 'Mazda MX-5 Cup', class: 'Touring', tank: 50, fuel: 1.7 },
    { label: 'Ferrari 296 Challenge', class: 'Cup', tank: 110, fuel: 3.0 },
    { label: 'Porsche 911 Cup (992.2)', class: 'Cup', tank: 100, fuel: 3.0 }
  ],
  LMU: [
    { label: 'Alpine A424', class: 'Hypercar', tank: 90, fuel: 4.6 },
    { label: 'Aston Martin Valkyrie AMR-LMH', class: 'Hypercar', tank: 90, fuel: 4.6 },
    { label: 'BMW M Hybrid V8', class: 'Hypercar', tank: 90, fuel: 4.6 },
    { label: 'Cadillac V-Series.R', class: 'Hypercar', tank: 90, fuel: 4.7 },
    { label: 'Ferrari 499P', class: 'Hypercar', tank: 90, fuel: 4.6 },
    { label: 'Genesis GMR-001', class: 'Hypercar', tank: 90, fuel: 4.6 },
    { label: 'Glickenhaus SCG 007', class: 'Hypercar', tank: 90, fuel: 4.7 },
    { label: 'Isotta Fraschini Tipo 6', class: 'Hypercar', tank: 90, fuel: 4.6 },
    { label: 'Lamborghini SC63', class: 'Hypercar', tank: 90, fuel: 4.6 },
    { label: 'Peugeot 9X8', class: 'Hypercar', tank: 90, fuel: 4.7 },
    { label: 'Peugeot 9X8 2024', class: 'Hypercar', tank: 90, fuel: 4.7 },
    { label: 'Porsche 963', class: 'Hypercar', tank: 90, fuel: 4.6 },
    { label: 'Toyota GR010-Hybrid', class: 'Hypercar', tank: 90, fuel: 4.6 },
    { label: 'Vanwall Vandervell 680', class: 'Hypercar', tank: 90, fuel: 4.8 },
    { label: 'ORECA 07 Gibson 2023', class: 'LMP2', tank: 75, fuel: 3.9 },
    { label: 'ORECA 07 Gibson 2024', class: 'LMP2', tank: 75, fuel: 3.9 },
    { label: 'ADESS-03', class: 'LMP3', tank: 70, fuel: 3.4 },
    { label: 'Duqueine D09', class: 'LMP3', tank: 70, fuel: 3.4 },
    { label: 'Ginetta G61-LT-P325-Evo', class: 'LMP3', tank: 70, fuel: 3.4 },
    { label: 'Ligier JS P325', class: 'LMP3', tank: 70, fuel: 3.4 },
    { label: 'Aston Martin Vantage AMR LMGT3 Evo', class: 'LMGT3', tank: 120, fuel: 3.4 },
    { label: 'BMW M4 LMGT3', class: 'LMGT3', tank: 120, fuel: 3.4 },
    { label: 'BMW M4 LMGT3 Evo', class: 'LMGT3', tank: 120, fuel: 3.4 },
    { label: 'Chevrolet Corvette Z06 LMGT3.R', class: 'LMGT3', tank: 120, fuel: 3.4 },
    { label: 'Ferrari 296 LMGT3', class: 'LMGT3', tank: 120, fuel: 3.35 },
    { label: 'Ferrari 296 LMGT3 Evo', class: 'LMGT3', tank: 120, fuel: 3.35 },
    { label: 'Ford Mustang LMGT3', class: 'LMGT3', tank: 120, fuel: 3.5 },
    { label: 'Ford Mustang LMGT3 Evo', class: 'LMGT3', tank: 120, fuel: 3.5 },
    { label: 'Lamborghini Huracan LMGT3 Evo 2', class: 'LMGT3', tank: 120, fuel: 3.45 },
    { label: 'Lexus RC F LMGT3', class: 'LMGT3', tank: 120, fuel: 3.45 },
    { label: 'Mercedes-AMG LMGT3', class: 'LMGT3', tank: 120, fuel: 3.45 },
    { label: 'McLaren 720S LMGT3 Evo', class: 'LMGT3', tank: 120, fuel: 3.35 },
    { label: 'Porsche 911 GT3 R LMGT3', class: 'LMGT3', tank: 120, fuel: 3.35 },
    { label: 'Aston Martin Vantage AMR GTE', class: 'GTE', tank: 100, fuel: 3.6 },
    { label: 'Chevrolet Corvette C8.R', class: 'GTE', tank: 100, fuel: 3.6 },
    { label: 'Ferrari 488 GTE Evo', class: 'GTE', tank: 100, fuel: 3.55 },
    { label: 'Porsche 911 RSR-19', class: 'GTE', tank: 100, fuel: 3.55 }
  ]
}

const sim = ref('ACC')
const car = ref('Ferrari 296 GT3 2023')
const assetFuelCars = ref({})
const presetIndex = ref(0)
const mode = ref('time')
const unit = ref('L')
const raceHours = ref(1)
const raceMinutes = ref(0)
const raceLaps = ref(20)
const lapMinutes = ref(2)
const lapSeconds = ref(5)
const fuelPerLap = ref(3.2)
const tank = ref(110)
const reserveLaps = ref(1)
const currentFuel = ref('')
const formationLap = ref(false)

const copy = computed(() => state.locale === 'en' ? {
  title: 'Fuel calculator',
  subtitle: 'Choose a simulator and car; adjust fuel per lap after a race-pace stint.',

  sim: 'Simulator',
  car: 'Car',
  preset: 'Class / preset',
  unit: 'Units',
  timeRace: 'Timed race',
  lapRace: 'Fixed laps',
  hours: 'Duration, hours',
  minutes: 'Duration, minutes',
  laps: 'Race laps',
  lapMin: 'Average lap, minutes',
  lapSec: 'Average lap, seconds',
  fuelLap: 'Fuel per lap',
  tank: 'Tank capacity',
  reserve: 'Reserve, laps',
  current: 'Fuel now',
  formation: 'Add formation lap',
  result: 'Result',
  recommended: 'Recommended',
  expected: 'Race laps',
  minimum: 'Minimum',
  stops: 'Pit stops',
  start: 'Start fuel',
  add: 'Add',
  ready: 'Calculation ready. Use race pace, not your best qualifying lap.',
  fill: 'Fill average lap and fuel per lap.',
  stopNeeded: 'Fuel does not fit in one tank; plan a pit stop.',
  formula: 'Formula: fuel = laps x fuel per lap + reserve.',
  check: 'Check consumption after 3-5 race-pace laps in the selected car.',
  fullTank: 'Full tank',
  stint: 'Stint'
} : {
  title: 'Калькулятор топлива',
  subtitle: 'Выбери симулятор и машину; расход за круг уточняй после боевого отрезка.',
  sim: 'Симулятор',
  car: 'Машина',
  preset: 'Класс / пресет',
  unit: 'Единицы',
  timeRace: 'Гонка по времени',
  lapRace: 'Гонка по кругам',
  hours: 'Длительность, часы',
  minutes: 'Длительность, минуты',
  laps: 'Кругов в гонке',
  lapMin: 'Средний круг, минуты',
  lapSec: 'Средний круг, секунды',
  fuelLap: 'Расход за круг',
  tank: 'Объем бака',
  reserve: 'Запас, круги',
  current: 'Топливо сейчас',
  formation: 'Добавить прогревочный круг',
  result: 'Результат',
  recommended: 'Рекомендовано',
  expected: 'Гоночные круги',
  minimum: 'Минимум',
  stops: 'Пит-стопы',
  start: 'Стартовая заправка',
  add: 'Долить',
  ready: 'Расчет готов. Используй боевой темп, а не лучший квалификационный круг.',
  fill: 'Заполни средний круг и расход.',
  stopNeeded: 'На старт весь объем не помещается: нужен пит-стоп.',
  formula: 'Формула: топливо = круги x расход за круг + запас.',
  check: 'Проверь расход после 3-5 боевых кругов в выбранной машине.',
  fullTank: 'Полный бак',
  stint: 'Стинт'
})

const simPresets = computed(() => presets[sim.value] || [])
const carOptions = computed(() => mergeCarLists(fuelCars[sim.value] || [], assetFuelCars.value[sim.value] || []))
const selectedPreset = computed(() => simPresets.value[Number(presetIndex.value)] || simPresets.value[0])
const selectedCarPreset = computed(() => carOptions.value.find((item) => item.label === car.value))
const lapSecondsTotal = computed(() => Math.max(0, Number(lapMinutes.value) * 60 + Number(lapSeconds.value)))
const expectedLaps = computed(() => {
  if (mode.value === 'laps') return Math.max(0, Math.ceil(Number(raceLaps.value) || 0))
  const raceSeconds = Math.max(0, Number(raceHours.value) * 3600 + Number(raceMinutes.value) * 60)
  if (!raceSeconds || !lapSecondsTotal.value) return 0
  return Math.ceil(raceSeconds / lapSecondsTotal.value)
})
const totalReserveLaps = computed(() => Math.max(0, Number(reserveLaps.value) || 0) + (formationLap.value ? 1 : 0))
const minimumFuel = computed(() => expectedLaps.value * Math.max(0, Number(fuelPerLap.value) || 0))
const recommendedFuel = computed(() => minimumFuel.value + totalReserveLaps.value * Math.max(0, Number(fuelPerLap.value) || 0))
const pitStops = computed(() => Number(tank.value) > 0 ? Math.max(0, Math.ceil(recommendedFuel.value / Number(tank.value)) - 1) : 0)
const fullTankLaps = computed(() => Number(tank.value) > 0 && Number(fuelPerLap.value) > 0 ? Math.floor(Number(tank.value) / Number(fuelPerLap.value)) : 0)
const stintLaps = computed(() => Math.ceil((expectedLaps.value + totalReserveLaps.value) / (pitStops.value + 1)) || 0)
const startFuel = computed(() => Math.min(recommendedFuel.value, Number(tank.value) || recommendedFuel.value))
const fuelToAdd = computed(() => currentFuel.value === '' ? null : Math.max(0, recommendedFuel.value - (Number(currentFuel.value) || 0)))
const presetHint = computed(() => state.locale === 'en' ? selectedPreset.value?.hintEn : selectedPreset.value?.hintRu)
const warning = computed(() => {
  if (!lapSecondsTotal.value || !Number(fuelPerLap.value)) return copy.value.fill
  if (Number(tank.value) > 0 && recommendedFuel.value > Number(tank.value)) return copy.value.stopNeeded
  return copy.value.ready
})

function formatFuel(value) {
  if (!Number.isFinite(value)) return `0 ${unit.value}`
  const fixed = value >= 100 ? value.toFixed(0) : value.toFixed(1)
  return `${fixed} ${unit.value}`
}

function handleSimChange() {
  presetIndex.value = 0
  car.value = carOptions.value[0]?.label || ''
  if (!applyCarPreset()) applyPreset()
}

function mergeCarLists(...lists) {
  const seen = new Set()
  return lists.flat().filter((item) => {
    const key = item.label.trim().toLowerCase()
    if (!key || seen.has(key)) return false
    seen.add(key)
    return true
  })
}

function fallbackPresetForClass(simName, className) {
  const normalized = String(className || '').toLowerCase()
  return (presets[simName] || []).find((item) => item.label.toLowerCase() === normalized)
    || (presets[simName] || []).find((item) => normalized.includes(item.label.toLowerCase()) || item.label.toLowerCase().includes(normalized))
    || (presets[simName] || [])[0]
    || { tank: 100, fuel: 3 }
}

function carsFromRaceAssets(config) {
  const result = {}
  Object.keys(presets).forEach((game) => {
    const gameConfig = game === 'ACC' ? config : config?.games?.[game]
    result[game] = (gameConfig?.classes || []).flatMap((assetClass) => {
      const fallback = fallbackPresetForClass(game, assetClass.name)
      return (assetClass.cars || []).map((label) => ({
        label,
        class: assetClass.name,
        tank: fallback.tank,
        fuel: fallback.fuel
      }))
    })
  })
  return result
}

function applyCarPreset() {
  const item = selectedCarPreset.value
  if (!item) return false
  const index = simPresets.value.findIndex((preset) => preset.label === item.class)
  if (index >= 0) presetIndex.value = index
  tank.value = item.tank
  fuelPerLap.value = item.fuel
  return true
}

function applyPreset() {
  const item = selectedPreset.value
  if (!item) return
  tank.value = item.tank
  fuelPerLap.value = item.fuel
}

watch(car, () => {
  applyCarPreset()
})

onMounted(async () => {
  try {
    assetFuelCars.value = carsFromRaceAssets(await api('/race-assets'))
  } catch {
    assetFuelCars.value = {}
  }
})
</script>

<template>
  <section class="section fuel-page">
    <div class="section-header">
      <div>
        <h1>{{ copy.title }}</h1>
        <p class="muted">{{ copy.subtitle }}</p>
      </div>
    </div>

    <div class="fuel-layout">
      <form class="card form fuel-form" @submit.prevent>
        <div class="form-row">
          <label class="field">
            <span>{{ copy.sim }}</span>
            <select v-model="sim" @change="handleSimChange">
              <option v-for="name in Object.keys(presets)" :key="name" :value="name">{{ name }}</option>
            </select>
          </label>
          <label class="field">
            <span>{{ copy.car }}</span>
            <input v-model="car" list="fuel-car-options" maxlength="120" />
            <datalist id="fuel-car-options">
              <option v-for="item in carOptions" :key="item.label" :value="item.label">{{ item.class }}</option>
            </datalist>
          </label>
        </div>

        <div class="form-row">
          <label class="field">
            <span>{{ copy.preset }}</span>
            <select v-model="presetIndex" @change="applyPreset">
              <option v-for="(item, index) in simPresets" :key="item.label" :value="index">{{ item.label }}</option>
            </select>
          </label>
          <label class="field">
            <span>{{ copy.unit }}</span>
            <select v-model="unit">
              <option value="L">L</option>
              <option value="gal">gal</option>
            </select>
          </label>
        </div>

        <div class="fuel-mode-switch">
          <label class="toggle-field"><input v-model="mode" type="radio" value="time" />{{ copy.timeRace }}</label>
          <label class="toggle-field"><input v-model="mode" type="radio" value="laps" />{{ copy.lapRace }}</label>
        </div>

        <div v-if="mode === 'time'" class="form-row">
          <label class="field"><span>{{ copy.hours }}</span><input v-model.number="raceHours" type="number" min="0" step="1" /></label>
          <label class="field"><span>{{ copy.minutes }}</span><input v-model.number="raceMinutes" type="number" min="0" step="1" /></label>
        </div>
        <div v-else class="form-row">
          <label class="field"><span>{{ copy.laps }}</span><input v-model.number="raceLaps" type="number" min="1" step="1" /></label>
        </div>

        <div class="form-row">
          <label class="field"><span>{{ copy.lapMin }}</span><input v-model.number="lapMinutes" type="number" min="0" step="1" /></label>
          <label class="field"><span>{{ copy.lapSec }}</span><input v-model.number="lapSeconds" type="number" min="0" max="59.999" step="0.001" /></label>
        </div>

        <div class="form-row">
          <label class="field"><span>{{ copy.fuelLap }}</span><input v-model.number="fuelPerLap" type="number" min="0" step="0.01" /></label>
          <label class="field"><span>{{ copy.tank }}</span><input v-model.number="tank" type="number" min="0" step="0.1" /></label>
        </div>

        <div class="form-row">
          <label class="field"><span>{{ copy.reserve }}</span><input v-model.number="reserveLaps" type="number" min="0" step="0.25" /></label>
          <label class="field"><span>{{ copy.current }}</span><input v-model="currentFuel" type="number" min="0" step="0.1" /></label>
        </div>

        <label class="toggle-field fuel-wide-toggle"><input v-model="formationLap" type="checkbox" />{{ copy.formation }}</label>
        <p class="fuel-note">{{ presetHint }}</p>
      </form>

      <aside class="card fuel-results">
        <div class="fuel-results-head">
          <h2>{{ copy.result }}</h2>
          <span>{{ sim }}<template v-if="car"> / {{ car }}</template></span>
        </div>

        <div class="fuel-metric is-primary">
          <Fuel :size="22" />
          <span>{{ copy.recommended }}</span>
          <strong>{{ formatFuel(recommendedFuel) }}</strong>
        </div>

        <div class="fuel-metrics-grid">
          <div class="fuel-metric">
            <TimerReset :size="20" />
            <span>{{ copy.expected }}</span>
            <strong>{{ expectedLaps }}</strong>
          </div>
          <div class="fuel-metric">
            <Calculator :size="20" />
            <span>{{ copy.minimum }}</span>
            <strong>{{ formatFuel(minimumFuel) }}</strong>
          </div>
          <div class="fuel-metric">
            <Gauge :size="20" />
            <span>{{ copy.stops }}</span>
            <strong>{{ pitStops }}</strong>
          </div>
          <div class="fuel-metric">
            <Fuel :size="20" />
            <span>{{ copy.start }}</span>
            <strong>{{ formatFuel(startFuel) }}</strong>
          </div>
        </div>

        <div class="fuel-summary">
          <p>{{ warning }}</p>
          <p>{{ copy.formula }}</p>
          <p>{{ copy.check }}</p>
          <p>{{ copy.add }}: <strong>{{ fuelToAdd === null ? '-' : formatFuel(fuelToAdd) }}</strong></p>
          <p>{{ copy.fullTank }}: <strong>{{ fullTankLaps }}</strong>. {{ copy.stint }}: <strong>{{ stintLaps }}</strong>.</p>
        </div>
      </aside>
    </div>
  </section>
</template>
