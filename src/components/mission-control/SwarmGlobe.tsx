import {
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import Globe, {
  type GlobeMethods,
} from "react-globe.gl";

import * as THREE from "three";

import {
  Maximize2,
  Minus,
  Plus,
} from "lucide-react";

import type {
  SatelliteTelemetry,
} from "../../data/mockMissionControl";

interface SwarmGlobeProps {
  satellites: SatelliteTelemetry[];
  selectedSatelliteId: string;
  onSelectSatellite: (id: string) => void;
  coordinatorId: string;
  activeLinks?: Array<[string, string]>;
  apiBaseUrl: string;
}

interface GlobeNode {
  id: string;
  lat: number;
  lng: number;
  altitude: number;
  altKm: number;
  state: string;
  role: string;
  battery: number;
  propellant: number;
  trust: number;
  linkQuality: number;
  neighbors: number;
  selected: boolean;
  coordinator: boolean;
}

interface GlobeArc {
  source: GlobeNode;
  target: GlobeNode;
}

interface RealOrbitNode {
  id: string;
  name: string;
  constellation: string;

  lat: number;
  lng: number;

  altitude: number;
  altKm: number;

  tleAgeHours: number;
  speedKmS: number;
}

interface RealOrbitApiResponse {
  mode: string;
  propagatedUtc: string;

  freshSatellites: number;

  countsByConstellation:
    Record<string, number>;

  satellites: Array<{
    id: string;
    name: string;
    constellation: string;
    tleAgeHours: number;

    position: {
      lat: number;
      lon: number;
      altKm: number;
    };

    velocity: {
      speedKmS: number;
    };
  }>;
}

type GlobeObject =
  | GlobeNode
  | RealOrbitNode;

interface OrbitPoint {
  lat: number;
  lng: number;
  altitude: number;
}

interface OrbitTrack {
  plane: string;
  points: OrbitPoint[];
}

const EARTH_RADIUS_KM = 6371;

const AMBIENT_TRAFFIC_COUNT = 900;

const PLANE_RAAN: Record<string, number> = {
  "PLANE A": 0,
  "PLANE B": 120,
  "PLANE C": 240,
};

function nodeColor(
  node: GlobeNode
): string {
  if (node.selected) {
    return "#FFFFFF";
  }

  if (
    node.state === "FAILED" ||
    node.state === "ISOLATED"
  ) {
    return "#FF384D";
  }

  if (
    node.state === "DEGRADED" ||
    node.state === "RECOVERING"
  ) {
    return "#FF8B3D";
  }

  if (
    node.state === "WARNING" ||
    node.state === "SUSPECTED"
  ) {
    return "#F6C453";
  }

  if (node.coordinator) {
    return "#8BE4FF";
  }

  return "#52CFFF";
}

const REAL_ORBIT_COLORS:
  Record<string, string> = {
    STARLINK: "#FF4655",
    ONEWEB: "#FF9A52",
    IRIDIUM: "#D879FF",
    KUIPER: "#FFD166",
    QIANFAN: "#70D9A2",
    GALILEO: "#E8EDF3",
  };

const REAL_DOT_GEOMETRY =
  new THREE.SphereGeometry(
    0.34,
    7,
    7
  );

const REAL_DOT_MATERIALS =
  new Map<
    string,
    THREE.MeshBasicMaterial
  >();

function getRealOrbitMaterial(
  constellation: string
) {
  const key =
    constellation.toUpperCase();

  const existing =
    REAL_DOT_MATERIALS.get(
      key
    );

  if (existing) {
    return existing;
  }

  const material =
    new THREE.MeshBasicMaterial({
      color:
        new THREE.Color(
          REAL_ORBIT_COLORS[
            key
          ] ?? "#A6AFB7"
        ),
      transparent: true,
      opacity: 0.82,
    });

  REAL_DOT_MATERIALS.set(
    key,
    material
  );

  return material;
}

function createRealOrbitDot(
  node: RealOrbitNode
): THREE.Mesh {
  const dot =
    new THREE.Mesh(
      REAL_DOT_GEOMETRY,
      getRealOrbitMaterial(
        node.constellation
      )
    );

  dot.scale.setScalar(
    node.constellation ===
      "STARLINK"
      ? 1
      : 0.92
  );

  return dot;
}

function createSatelliteObject(
  node: GlobeNode
): THREE.Group {
  const group =
    new THREE.Group();

  const color =
    new THREE.Color(
      nodeColor(node)
    );

  const scale =
    node.selected
      ? 1.4
      : node.coordinator
        ? 1.2
        : 1;

  // Main spacecraft body
  const body =
    new THREE.Mesh(
      new THREE.BoxGeometry(
        1.15 * scale,
        0.85 * scale,
        0.85 * scale
      ),
      new THREE.MeshBasicMaterial({
        color,
      })
    );

  group.add(body);

  // Solar panels
  const panelMaterial =
    new THREE.MeshBasicMaterial({
      color:
        new THREE.Color(
          "#176A9A"
        ),
      transparent: true,
      opacity: 0.95,
    });

  const leftPanel =
    new THREE.Mesh(
      new THREE.BoxGeometry(
        1.8 * scale,
        0.10 * scale,
        0.72 * scale
      ),
      panelMaterial
    );

  leftPanel.position.x =
    -1.55 * scale;

  group.add(leftPanel);

  const rightPanel =
    leftPanel.clone();

  rightPanel.position.x =
    1.55 * scale;

  group.add(rightPanel);

  // Tiny restrained glow
  const glow =
    new THREE.Mesh(
      new THREE.SphereGeometry(
        1.45 * scale,
        16,
        16
      ),
      new THREE.MeshBasicMaterial({
        color,
        transparent: true,
        opacity:
          node.selected
            ? 0.12
            : 0.045,
        depthWrite: false,
        blending:
          THREE.AdditiveBlending,
      })
    );

  group.add(glow);

  return group;
}

function buildOrbitTracks(
  satellites: SatelliteTelemetry[]
): OrbitTrack[] {
  const seen =
    new Set<string>();

  const tracks:
    OrbitTrack[] = [];

  for (
    const satellite of satellites
  ) {
    if (
      seen.has(
        satellite.plane
      )
    ) {
      continue;
    }

    seen.add(
      satellite.plane
    );

    const inclination =
      (satellite.inclinationDeg *
        Math.PI) /
      180;

    const raanDeg =
      PLANE_RAAN[
        satellite.plane
      ] ??
      satellite.planeIndex *
        120;

    const raan =
      (raanDeg *
        Math.PI) /
      180;

    const altitude =
      satellite.altitudeKm /
      EARTH_RADIUS_KM;

    const points:
      OrbitPoint[] = [];

    for (
      let degree = 0;
      degree <= 360;
      degree += 3
    ) {
      const u =
        (degree *
          Math.PI) /
        180;

      const latitude =
        Math.asin(
          Math.sin(
            inclination
          ) *
            Math.sin(u)
        );

      const longitude =
        Math.atan2(
          Math.cos(
            inclination
          ) *
            Math.sin(u),
          Math.cos(u)
        ) + raan;

      let lng =
        (longitude *
          180) /
        Math.PI;

      while (lng > 180) {
        lng -= 360;
      }

      while (lng < -180) {
        lng += 360;
      }

      points.push({
        lat:
          (latitude *
            180) /
          Math.PI,
        lng,
        altitude,
      });
    }

    tracks.push({
      plane:
        satellite.plane,
      points,
    });
  }

  return tracks;
}

function createAmbientTrafficCloud(
  count: number
): THREE.Points {
  // Fixed seed = dots stay stable.
  let seed =
    0xA57A1234;

  const random = () => {
    seed =
      (1664525 * seed +
        1013904223) >>>
      0;

    return (
      seed /
      4294967296
    );
  };

  const positions =
    new Float32Array(
      count * 3
    );

  for (
    let index = 0;
    index < count;
    index += 1
  ) {
    const polarPopulation =
      random() < 0.22;

    const inclinationDeg =
      polarPopulation
        ? 78 +
          random() * 20
        : 18 +
          random() * 58;

    const inclination =
      (inclinationDeg *
        Math.PI) /
      180;

    const anomaly =
      random() *
      Math.PI *
      2;

    const raan =
      random() *
      Math.PI *
      2;

    const altitudeKm =
      random() < 0.72
        ? 430 +
          random() * 280
        : 710 +
          random() * 550;

    // three-globe globe radius is ~100
    const radius =
      100 *
      (1 +
        altitudeKm /
          EARTH_RADIUS_KM);

    const orbitalX =
      radius *
      Math.cos(anomaly);

    const orbitalY =
      radius *
      Math.sin(anomaly) *
      Math.cos(
        inclination
      );

    const orbitalZ =
      radius *
      Math.sin(anomaly) *
      Math.sin(
        inclination
      );

    const x =
      orbitalX *
        Math.cos(raan) -
      orbitalY *
        Math.sin(raan);

    const y =
      orbitalX *
        Math.sin(raan) +
      orbitalY *
        Math.cos(raan);

    const z =
      orbitalZ;

    const offset =
      index * 3;

    positions[offset] =
      x;

    positions[
      offset + 1
    ] = y;

    positions[
      offset + 2
    ] = z;
  }

  const geometry =
    new THREE.BufferGeometry();

  geometry.setAttribute(
    "position",
    new THREE.BufferAttribute(
      positions,
      3
    )
  );

  const material =
    new THREE.PointsMaterial({
      color:
        new THREE.Color(
          "#829AA8"
        ),
      size: 0.36,
      sizeAttenuation: true,
      transparent: true,
      opacity: 0.30,
      depthWrite: false,
      blending:
        THREE.AdditiveBlending,
    });

  const cloud =
    new THREE.Points(
      geometry,
      material
    );

  cloud.frustumCulled =
    false;

  return cloud;
}

export default function SwarmGlobe({
  satellites,
  selectedSatelliteId,
  onSelectSatellite,
  coordinatorId,
  activeLinks = [],
  apiBaseUrl,
}: SwarmGlobeProps) {
  const containerRef =
    useRef<HTMLDivElement>(
      null
    );

  const globeRef =
    useRef<
      GlobeMethods | undefined
    >(undefined);

  const [
    size,
    setSize,
  ] = useState({
    width: 900,
    height: 650,
  });

  const [
    showAmbientTraffic,
    setShowAmbientTraffic,
  ] = useState(false);

  const ambientTrafficCloud =
    useMemo(
      () =>
        createAmbientTrafficCloud(
          AMBIENT_TRAFFIC_COUNT
        ),
      []
    );

  const [
    showRealOrbits,
    setShowRealOrbits,
  ] = useState(true);

  const [
    realOrbitData,
    setRealOrbitData,
  ] =
    useState<RealOrbitApiResponse | null>(
      null
    );

  const [
    realOrbitError,
    setRealOrbitError,
  ] =
    useState<string | null>(
      null
    );

  useEffect(() => {
    let cancelled = false;

    const loadRealOrbits =
      async () => {
        try {
          const response =
            await fetch(
              `${apiBaseUrl}/api/orbits/live?limit=200`
            );

          if (!response.ok) {
            throw new Error(
              `HTTP ${response.status}`
            );
          }

          const data =
            (await response.json()) as RealOrbitApiResponse;

          if (cancelled) {
            return;
          }

          setRealOrbitData(
            data
          );

          setRealOrbitError(
            null
          );
        } catch (error) {
          if (cancelled) {
            return;
          }

          setRealOrbitError(
            error instanceof Error
              ? error.message
              : "Real orbit feed unavailable"
          );
        }
      };

    loadRealOrbits();

    const timer =
      window.setInterval(
        loadRealOrbits,
        5000
      );

    return () => {
      cancelled = true;

      window.clearInterval(
        timer
      );
    };
  }, [apiBaseUrl]);

  useEffect(() => {
    const element =
      containerRef.current;

    if (!element) {
      return;
    }

    const resize = () => {
      const rect =
        element.getBoundingClientRect();

      setSize({
        width: Math.max(
          1,
          Math.floor(
            rect.width
          )
        ),
        height: Math.max(
          1,
          Math.floor(
            rect.height
          )
        ),
      });
    };

    resize();

    const observer =
      new ResizeObserver(
        resize
      );

    observer.observe(
      element
    );

    return () =>
      observer.disconnect();
  }, []);

  const nodes =
    useMemo<
      GlobeNode[]
    >(() => {
      return satellites.flatMap(
        (satellite) => {
          if (
            !satellite.position
          ) {
            return [];
          }

          const altitudeKm =
            satellite.position
              .altKm ??
            satellite.altitudeKm;

          return [
            {
              id:
                satellite.id,

              lat:
                satellite
                  .position.lat,

              lng:
                satellite
                  .position.lon,

              altitude:
                altitudeKm /
                EARTH_RADIUS_KM,

              altKm:
                altitudeKm,

              state:
                satellite.state,

              role:
                satellite.role,

              battery:
                satellite.battery,

              propellant:
                satellite
                  .propellant,

              trust:
                satellite.trust,

              linkQuality:
                satellite.network
                  .linkQuality,

              neighbors:
                satellite.network
                  .neighbors,

              selected:
                satellite.id ===
                selectedSatelliteId,

              coordinator:
                satellite.id ===
                coordinatorId,
            },
          ];
        }
      );
    }, [
      satellites,
      selectedSatelliteId,
      coordinatorId,
    ]);

  const nodeMap =
    useMemo(
      () =>
        new Map(
          nodes.map(
            (node) => [
              node.id,
              node,
            ]
          )
        ),
      [nodes]
    );

  const arcs =
    useMemo<
      GlobeArc[]
    >(() => {
      return activeLinks.flatMap(
        ([
          sourceId,
          targetId,
        ]) => {
          const source =
            nodeMap.get(
              sourceId
            );

          const target =
            nodeMap.get(
              targetId
            );

          if (
            !source ||
            !target
          ) {
            return [];
          }

          return [
            {
              source,
              target,
            },
          ];
        }
      );
    }, [
      activeLinks,
      nodeMap,
    ]);

  const orbitTracks =
    useMemo(
      () =>
        buildOrbitTracks(
          satellites
        ),
      [satellites]
    );

  const realOrbitNodes =
    useMemo<
      RealOrbitNode[]
    >(() => {
      if (
        !showRealOrbits ||
        !realOrbitData
      ) {
        return [];
      }

      return realOrbitData.satellites.map(
        (satellite) => ({
          id:
            satellite.id,

          name:
            satellite.name,

          constellation:
            satellite.constellation,

          lat:
            satellite.position.lat,

          lng:
            satellite.position.lon,

          altKm:
            satellite.position.altKm,

          altitude:
            satellite.position.altKm /
            EARTH_RADIUS_KM,

          tleAgeHours:
            satellite.tleAgeHours,

          speedKmS:
            satellite.velocity.speedKmS,
        })
      );
    }, [
      realOrbitData,
      showRealOrbits,
    ]);

  const globeObjects =
    useMemo<
      GlobeObject[]
    >(
      () => [
        ...nodes,
        ...realOrbitNodes,
      ],
      [
        nodes,
        realOrbitNodes,
      ]
    );

  const alertNodes =
    useMemo(
      () =>
        nodes.filter(
          (node) =>
            node.selected ||
            node.state !==
              "NOMINAL"
        ),
      [nodes]
    );

  const labelNodes =
    useMemo(
      () =>
        nodes.filter(
          (node) =>
            node.selected ||
            node.coordinator ||
            node.state !==
              "NOMINAL"
        ),
      [nodes]
    );

  const selectedNode =
    nodes.find(
      (node) =>
        node.id ===
        selectedSatelliteId
    ) ?? null;

  const setupControls =
    () => {
      const globe =
        globeRef.current;

      if (!globe) {
        return;
      }

      const controls =
        globe.controls();

      controls.autoRotate =
        true;

      controls.autoRotateSpeed =
        0.28;

      controls.enableDamping =
        true;

      controls.dampingFactor =
        0.05;

      controls.rotateSpeed =
        0.5;

      controls.zoomSpeed =
        0.65;

      controls.enablePan =
        false;

      globe.pointOfView(
        {
          lat: 18,
          lng: 78,
          altitude: 2.2,
        },
        0
      );
    };

  const focusNode = (
    node: GlobeNode
  ) => {
    const globe =
      globeRef.current;

    if (!globe) {
      return;
    }

    globe.pointOfView(
      {
        lat: node.lat,
        lng: node.lng,
        altitude: 1.75,
      },
      750
    );
  };

  const zoom = (
    amount: number
  ) => {
    const globe =
      globeRef.current;

    if (!globe) {
      return;
    }

    const current =
      globe.pointOfView();

    globe.pointOfView(
      {
        lat:
          current.lat,
        lng:
          current.lng,
        altitude:
          Math.max(
            1.15,
            Math.min(
              4,
              current.altitude +
                amount
            )
          ),
      },
      350
    );
  };

  const resetView =
    () => {
      globeRef.current?.pointOfView(
        {
          lat: 18,
          lng: 78,
          altitude: 2.2,
        },
        700
      );
    };

  return (
    <div
      ref={containerRef}
      className="relative w-full h-full min-h-[500px] overflow-hidden bg-[#02050A]"
    >
      {nodes.length >
      0 ? (
        <Globe
          ref={globeRef}

          width={
            size.width
          }

          height={
            size.height
          }

          backgroundColor="#02050A"

          backgroundImageUrl="/globe/night-sky.png"

          globeImageUrl="/globe/earth-night.jpg"

          bumpImageUrl="/globe/earth-topology.png"

          showAtmosphere

          atmosphereColor="#4E9BD6"

          atmosphereAltitude={
            0.13
          }

          animateIn={
            false
          }

          onGlobeReady={
            setupControls
          }

          customLayerData={
            showAmbientTraffic
              ? [
                  ambientTrafficCloud,
                ]
              : []
          }

          customThreeObject={(
            item
          ) =>
            item as THREE.Object3D
          }

          objectsData={
            globeObjects
          }

          objectLat={(item) =>
            (
              item as GlobeNode
            ).lat
          }

          objectLng={(item) =>
            (
              item as GlobeNode
            ).lng
          }

          objectAltitude={(
            item
          ) =>
            (
              item as GlobeNode
            ).altitude
          }

          objectFacesSurfaces={
            true
          }

          objectThreeObject={(
            item
          ) => {
            const object =
              item as GlobeObject;

            if (
              "constellation"
              in object
            ) {
              return createRealOrbitDot(
                object
              );
            }

            return createSatelliteObject(
              object
            );
          }}

          objectLabel={(
            item
          ) => {
            const object =
              item as GlobeObject;

            if (
              "constellation"
              in object
            ) {
              const color =
                REAL_ORBIT_COLORS[
                  object.constellation
                ] ??
                "#A6AFB7";

              return `
                <div style="
                  min-width:190px;
                  padding:10px 12px;
                  background:rgba(3,7,12,.96);
                  border:1px solid ${color}55;
                  border-radius:8px;
                  color:#EAF4FA;
                  font-family:Inter,system-ui,sans-serif;
                  font-size:11px;
                  line-height:1.55;
                ">
                  <b>${object.name}</b><br/>

                  <span style="color:${color}">
                    ${object.constellation}
                  </span><br/>

                  <span style="color:#8DA4B4">
                    ${object.lat.toFixed(3)}°,
                    ${object.lng.toFixed(3)}°
                  </span><br/>

                  <span style="color:#8DA4B4">
                    ALT ${object.altKm.toFixed(1)} km
                  </span><br/>

                  <span style="color:#8DA4B4">
                    SPD ${object.speedKmS.toFixed(3)} km/s
                  </span><br/>

                  <span style="color:#657785">
                    TLE ${object.tleAgeHours.toFixed(1)}h old
                  </span>
                </div>
              `;
            }

            const node =
              object as GlobeNode;

            return `
              <div style="
                min-width:180px;
                padding:10px 12px;
                background:rgba(3,7,12,.96);
                border:1px solid rgba(100,200,255,.24);
                border-radius:8px;
                color:#EAF4FA;
                font-family:Inter,system-ui,sans-serif;
                font-size:11px;
                line-height:1.55;
              ">
                <b>${node.id}</b><br/>

                <span style="color:#8DA4B4">
                  ${node.lat.toFixed(3)}°,
                  ${node.lng.toFixed(3)}°
                </span><br/>

                <span style="color:#8DA4B4">
                  ALT ${node.altKm.toFixed(1)} km
                </span><br/>

                <span style="color:${nodeColor(node)}">
                  ${node.state} · ${node.role}
                </span>
              </div>
            `;
          }}

          onObjectClick={(
            item
          ) => {
            const object =
              item as GlobeObject;

            if (
              "constellation"
              in object
            ) {
              return;
            }

            onSelectSatellite(
              object.id
            );

            focusNode(
              object
            );
          }}

          pathsData={
            orbitTracks
          }

          pathPoints={(
            item
          ) =>
            (
              item as OrbitTrack
            ).points
          }

          pathPointLat={(
            point
          ) =>
            (
              point as OrbitPoint
            ).lat
          }

          pathPointLng={(
            point
          ) =>
            (
              point as OrbitPoint
            ).lng
          }

          pathPointAlt={(
            point
          ) =>
            (
              point as OrbitPoint
            ).altitude
          }

          pathColor={() =>
            "rgba(81,195,255,0.30)"
          }

          pathStroke={
            0.40
          }

          pathResolution={
            2
          }

          pathTransitionDuration={
            0
          }

          arcsData={
            arcs
          }

          arcStartLat={(
            item
          ) =>
            (
              item as GlobeArc
            ).source.lat
          }

          arcStartLng={(
            item
          ) =>
            (
              item as GlobeArc
            ).source.lng
          }

          arcStartAltitude={(
            item
          ) =>
            (
              item as GlobeArc
            ).source.altitude
          }

          arcEndLat={(
            item
          ) =>
            (
              item as GlobeArc
            ).target.lat
          }

          arcEndLng={(
            item
          ) =>
            (
              item as GlobeArc
            ).target.lng
          }

          arcEndAltitude={(
            item
          ) =>
            (
              item as GlobeArc
            ).target.altitude
          }

          arcColor={() =>
            "rgba(82,207,255,0.58)"
          }

          arcStroke={
            0.24
          }

          arcDashLength={
            0.45
          }

          arcDashGap={
            0.26
          }

          arcDashAnimateTime={
            2200
          }

          ringsData={
            alertNodes
          }

          ringLat={(
            item
          ) =>
            (
              item as GlobeNode
            ).lat
          }

          ringLng={(
            item
          ) =>
            (
              item as GlobeNode
            ).lng
          }

          ringAltitude={(
            item
          ) =>
            (
              item as GlobeNode
            ).altitude
          }

          ringColor={(
            item: object
          ) => {
            const node =
              item as GlobeNode;

            if (
              node.selected
            ) {
              return [
                "rgba(255,255,255,.75)",
                "rgba(255,255,255,.01)",
              ];
            }

            return [
              "rgba(255,56,77,.82)",
              "rgba(255,56,77,.01)",
            ];
          }}

          ringMaxRadius={(
            item
          ) =>
            (
              item as GlobeNode
            ).selected
              ? 2.2
              : 3.8
          }

          ringPropagationSpeed={
            1.6
          }

          ringRepeatPeriod={
            1400
          }

          labelsData={
            labelNodes
          }

          labelLat={(
            item
          ) =>
            (
              item as GlobeNode
            ).lat
          }

          labelLng={(
            item
          ) =>
            (
              item as GlobeNode
            ).lng
          }

          labelAltitude={(
            item
          ) =>
            (
              item as GlobeNode
            ).altitude +
            0.018
          }

          labelText={(
            item
          ) =>
            (
              item as GlobeNode
            ).id
          }

          labelColor={(
            item: object
          ) =>
            nodeColor(
              item as GlobeNode
            )
          }

          labelSize={
            0.42
          }

          labelDotRadius={
            0.10
          }

          labelIncludeDot={
            false
          }
        />
      ) : (
        <div className="absolute inset-0 grid place-items-center">
          <p className="text-xs text-[#8296A5]">
            Waiting for orbital telemetry...
          </p>
        </div>
      )}

      <div className="absolute top-5 left-5 pointer-events-none">
        <div className="text-[9px] uppercase tracking-[0.18em] text-[#607382]">
          ASTRANET SWARM
        </div>

        <div className="mt-1 text-sm font-semibold text-white">
          Orbital Network Live
        </div>
      </div>

      <div className="absolute right-5 top-20 z-30 flex flex-col gap-2">
        <button
          type="button"
          onClick={() =>
            zoom(-0.22)
          }
          title="Zoom in"
          className="w-10 h-10 rounded-lg border border-white/10 bg-[#05080D]/80 grid place-items-center hover:bg-white/10"
        >
          <Plus className="w-4 h-4" />
        </button>

        <button
          type="button"
          onClick={() =>
            zoom(0.22)
          }
          title="Zoom out"
          className="w-10 h-10 rounded-lg border border-white/10 bg-[#05080D]/80 grid place-items-center hover:bg-white/10"
        >
          <Minus className="w-4 h-4" />
        </button>

        <button
          type="button"
          onClick={
            resetView
          }
          title="Reset camera"
          className="w-10 h-10 rounded-lg border border-white/10 bg-[#05080D]/80 grid place-items-center hover:bg-white/10"
        >
          <Maximize2 className="w-4 h-4" />
        </button>
      </div>

      <div className="absolute bottom-5 left-5 rounded-lg border border-[#52CFFF]/15 bg-[#03070C]/72 backdrop-blur-md px-3 py-2">
        <div className="flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-[#52CFFF] animate-pulse" />

          <span className="text-[10px] tracking-[0.15em] text-[#A6D8EC]">
            LIVE DIGITAL TWIN
          </span>
        </div>

        <div className="mt-1 text-[10px] text-[#667A88]">
          {nodes.length} ASTRANET
          {" · "}
          {orbitTracks.length} planes
          {" · "}
          {arcs.length} links
        </div>

        <button
          type="button"
          onClick={() =>
            setShowRealOrbits(
              (current) =>
                !current
            )
          }
          className="mt-2 block text-[9px] tracking-[0.10em] text-[#9AAEBB] hover:text-white transition-colors"
        >
          {showRealOrbits
            ? `● REAL ORBITS ${realOrbitNodes.length} ON`
            : "○ REAL ORBITS OFF"}
        </button>

        {showRealOrbits && realOrbitData && (
          <div className="mt-2 grid grid-cols-2 gap-x-3 gap-y-1 text-[8px] tracking-[0.06em]">
            {Object.entries(
              realOrbitData.countsByConstellation
            ).map(
              ([name, count]) => (
                <div
                  key={name}
                  className="flex items-center gap-1.5"
                >
                  <span
                    className="w-1.5 h-1.5 rounded-full"
                    style={{
                      backgroundColor:
                        REAL_ORBIT_COLORS[
                          name
                        ] ??
                        "#A6AFB7",
                    }}
                  />

                  <span className="text-[#738793]">
                    {name} {count}
                  </span>
                </div>
              )
            )}
          </div>
        )}

        {realOrbitError && (
          <div className="mt-2 text-[8px] text-[#FF7B88]">
            REAL ORBIT FEED: {realOrbitError}
          </div>
        )}

        <button
          type="button"
          onClick={() =>
            setShowAmbientTraffic(
              (current) =>
                !current
            )
          }
          className="mt-2 text-[9px] tracking-[0.10em] text-[#78909F] hover:text-[#D3E8F2] transition-colors"
        >
          {showAmbientTraffic
            ? `● AMBIENT SIM ${AMBIENT_TRAFFIC_COUNT} ON`
            : "○ AMBIENT TRAFFIC OFF"}
        </button>
      </div>

      {selectedNode && (
        <div className="absolute bottom-5 right-5 min-w-[170px] rounded-lg border border-white/10 bg-[#03070C]/72 backdrop-blur-md px-3 py-2 pointer-events-none">
          <div className="text-[9px] uppercase tracking-[0.14em] text-[#657785]">
            Selected
          </div>

          <div className="mt-1 text-xs font-semibold text-white">
            {selectedNode.id}
          </div>

          <div className="mt-1 font-mono text-[10px] leading-5 text-[#9DB2C0]">
            LAT{" "}
            {selectedNode.lat.toFixed(
              2
            )}
            °
            <br />

            LON{" "}
            {selectedNode.lng.toFixed(
              2
            )}
            °
            <br />

            ALT{" "}
            {selectedNode.altKm.toFixed(
              1
            )}{" "}
            km
          </div>
        </div>
      )}
    </div>
  );
}
