// Silverstone Circuit for TrackLayout3D.
// Centre line and corner positions: F1 timing map (metres, x east, y north), start line first.
// DRS zones: FIA event notes — activation 30 m after T5 and 55 m after T14; they end at the braking zones.
// Sector lines: where F1's two intermediate timing lines cross the track, measured from public timing data
// (OpenF1, 2023 British GP qualifying: six cars' positions at the end of their first and second sector,
// averaged; they agree within 10 m). ACC splits the lap on the same two straights.
export default {
  id: 'silverstone',
  name: 'Silverstone Circuit',
  lapKm: 5.891,
  /** Which way the camera looks at rest, degrees from east towards north: 0 puts east at the top, as on F1's own map. */
  yaw: 0,
  points:
    '-176,121 -83,244 8,375 41,413 70,435 93,445 121,451 164,452 241,444 269,445 304,453 326,463 355,482 415,540 ' +
    '450,570 470,585 487,590 502,589 513,585 528,571 537,549 544,504 549,493 563,479 573,474 580,473 587,476 599,486 ' +
    '611,504 619,521 629,555 633,578 633,605 628,631 622,651 612,670 597,692 570,719 484,788 181,1053 157,1071 132,1086 ' +
    '110,1093 91,1095 73,1094 58,1089 48,1084 35,1072 22,1045 17,993 12,975 0,958 -19,947 -36,944 -53,951 -63,961 -68,968 ' +
    '-76,991 -77,1014 -70,1048 -58,1079 -31,1129 -10,1159 15,1188 42,1212 76,1236 125,1258 179,1273 230,1280 380,1296 ' +
    '481,1309 522,1312 545,1310 582,1299 603,1286 623,1270 640,1248 654,1222 667,1185 683,1116 692,1059 697,994 701,896 ' +
    '705,865 715,819 744,741 752,711 754,691 752,668 736,593 733,560 735,539 738,528 747,508 768,471 777,447 779,429 ' +
    '778,417 774,402 766,384 756,368 743,354 699,328 676,311 651,284 633,260 595,190 409,-194 345,-314 325,-346 297,-379 ' +
    '273,-397 245,-409 218,-411 195,-407 173,-396 150,-377 131,-352 104,-305 87,-277 50,-227 -3,-161 -41,-118 -56,-103 ' +
    '-77,-93 -97,-92 -110,-96 -134,-112 -144,-115 -156,-115 -169,-111 -183,-105 -194,-96 -210,-75 -226,-40 -230,-23 ' +
    '-231,3 -228,27 -222,49 -214,66 -171,128',
  corners: [
    { n: 1, name: 'Abbey', x: 119, y: 450 },
    { n: 2, name: 'Farm', x: 277, y: 446 },
    { n: 3, name: 'Village', x: 485, y: 590 },
    { n: 4, name: 'The Loop', x: 580, y: 473 },
    { n: 5, name: 'Aintree', x: 623, y: 646 },
    { n: 6, name: 'Brooklands', x: 63, y: 1091 },
    { n: 7, name: 'Luffield', x: -57, y: 954 },
    { n: 8, name: 'Woodcote', x: 76, y: 1236 },
    { n: 9, name: 'Copse', x: 589, y: 1295 },
    { n: 10, name: 'Maggotts', x: 730, y: 778 },
    { n: 11, name: 'Maggotts', x: 754, y: 691 },
    { n: 12, name: 'Becketts', x: 734, y: 548 },
    { n: 13, name: 'Becketts', x: 778, y: 416 },
    { n: 14, name: 'Chapel', x: 681, y: 315 },
    { n: 15, name: 'Stowe', x: 240, y: -410 },
    { n: 16, name: 'Vale', x: -62, y: -99 },
    { n: 17, name: 'Club', x: -144, y: -115 },
    { n: 18, name: 'Club', x: -231, y: -11 }
  ],
  // End of sector 1 on the Wellington Straight just before Brooklands, end of sector 2 on the Hangar Straight just after Chapel.
  sectorLines: [
    { x: 189, y: 1045 },
    { x: 609, y: 219 }
  ],
  // [corner number, metres]: from 30 m after Aintree to the braking for Brooklands, and so on.
  zones: [
    { id: 'DRS 1', from: [5, 30], to: [6, -95] },
    { id: 'DRS 2', from: [14, 55], to: [15, -110] }
  ]
}
