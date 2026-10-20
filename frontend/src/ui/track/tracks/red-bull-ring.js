// Red Bull Ring, Grand Prix layout, for TrackLayout3D.
// Centre line and corner positions: F1 timing map (metres, x east, y north). The lap starts at the start line,
// where Assetto Corsa starts and ends it; F1's own timing line is the finish line, 120 m before it.
// Corner names: the circuit's own list (redbullring.com, October 2026). They are sponsors' names and change
// over the years: older simulators still say Castrol Edge, Remus or Würth. Turns 5, 6, 8 and 10 have no name there.
// Sector lines: the timing gates of the simulator the league races here (Assetto Corsa, Kunos Red Bull Ring,
// layout GP - LFM), read from the track's own files and laid onto this map (its driving line fits the centre
// line within 2 m). The first one is where F1's first intermediate line is (5 m apart, public timing data of the
// 2023 Austrian GP qualifying); the second one stands 80 m earlier than F1's.
// DRS zones: FIA event notes of the 2024 Austrian GP - activation 102 m after T1, 100 m after T3 and 106 m after T10;
// they end where F1 cars brake for the next corner (the same qualifying session). The league's own layout runs without DRS.
export default {
  id: 'red-bull-ring',
  name: 'Red Bull Ring',
  lapKm: 4.326,
  /** Which way the camera looks at rest, degrees from east towards north: 90 puts north at the top, as on F1's own map. */
  yaw: 90,
  points:
    '-5,-152 -268,-223 -287,-224 -302,-222 -324,-210 -331,-202 -354,-161 -492,49 -549,157 -610,285 -631,322 -651,351 ' +
    '-678,382 -722,427 -814,516 -822,527 -823,535 -823,541 -819,549 -812,554 -802,559 -756,565 -699,568 -646,566 ' +
    '-552,554 -373,520 -278,506 -203,498 -69,494 -52,491 -36,483 -27,471 -24,455 -26,442 -37,421 -55,398 -73,381 ' +
    '-89,370 -118,355 -162,342 -202,339 -249,344 -349,361 -395,364 -422,361 -432,356 -454,343 -466,329 -476,305 ' +
    '-478,278 -473,246 -465,222 -424,155 -401,122 -375,98 -352,87 -333,85 -324,86 -298,94 -277,108 -200,175 -176,190 ' +
    '-140,201 -101,204 -57,206 280,211 306,210 330,205 341,201 368,184 384,165 396,142 422,36 420,6 412,-14 402,-27 ' +
    '393,-34 371,-45 326,-62',
  corners: [
    { n: 1, name: 'Niki Lauda', x: -306, y: -221 },
    { n: 2, name: 'Münzer', x: -631, y: 322 },
    { n: 3, name: 'Interwetten', x: -821, y: 546 },
    { n: 4, name: 'Rauch', x: -27, y: 469 },
    { n: 5, x: -147, y: 346 },
    { n: 6, x: -463, y: 332 },
    { n: 7, name: 'Graz', x: -327, y: 85 },
    { n: 8, x: -162, y: 195 },
    { n: 9, name: 'Jochen Rindt', x: 367, y: 185 },
    { n: 10, x: 420, y: 9 }
  ],
  // End of sector 1 on the climb to T3, end of sector 2 on the way from T6 down to T7.
  sectorLines: [
    { x: -728, y: 433 },
    { x: -460, y: 213 }
  ],
  // [corner number, metres]; the third zone runs through the start line.
  zones: [
    { id: 'DRS 1', from: [1, 102], to: [3, -115] },
    { id: 'DRS 2', from: [3, 100], to: [4, -110] },
    { id: 'DRS 3', from: [10, 106], to: [1, -100] }
  ]
}
