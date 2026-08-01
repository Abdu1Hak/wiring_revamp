export interface Pin {
  name: string;             // "VCC", "GND", "TRIG", "ECHO", "anode", "cathode", "pin1", "pin2"
  type:
    | "power"               // VCC / 5V / 3.3V supply pins
    | "ground"              // GND pins
    | "digital_input"       // accepts digital signal (e.g. TRIG on HC-SR04)
    | "digital_output"      // sends digital signal (e.g. ECHO on HC-SR04)
    | "digital_io"          // bidirectional digital (e.g. GPIO on boards)
    | "analog_input"        // reads analog voltage (e.g. photoresistor signal)
    | "analog_output"       // sends analog/PWM signal
    | "data"                // generic data pin on simple components (e.g. DHT11 data)
    | "passive";            // resistor/capacitor leads — no polarity logic
  voltage?: number;          // operating voltage for this pin (5, 3.3, etc.)
  required: boolean;         // must be connected for the component to work
  notes?: string;            // "needs minimum 10μs HIGH pulse", "outputs 5V TTL"
}

export interface PowerRequirements {
  voltage: number;                    // nominal operating voltage
  voltage_tolerance?: [number, number]; // [min, max] acceptable voltage, e.g. [4.5, 5.5]
  current_mA: number;                 // typical operating current draw
  current_max_mA?: number;            // peak / startup current draw
}

export interface Constraint {
  type:
    | "requires_resistor"
    | "requires_level_shifter"
    | "requires_pullup"
    | "requires_capacitor"
    | "requires_decoupling"
    | "voltage_mismatch_risk"
    | "max_current_exceeded";
  condition: string;        // when does this apply: "LED connected without series resistor"
  resolution: string;       // what to do: "Add 220Ω resistor in series with LED anode"
  auto_fixable: boolean;    // true = system can add the fix component automatically
  fix_component_id?: string; // which component to auto-add: "resistor-220"
  severity: "info" | "warning" | "danger";
}

export interface Component {
  id: string;
  name: string;
  category:
    | "board"
    | "sensor"
    | "output"
    | "passive"
    | "actuator"
    | "display"
    | "communication"
    | "input"
    | "platform";
  description: string;          // one-line, beginner-friendly
  pins: Pin[];
  power: PowerRequirements;
  constraints: Constraint[];
  compatible_boards: string[];  // ["arduino-uno", "esp32-devkit"]
  tags: string[];               // ["distance", "ultrasonic", "proximity"]
  _needs_review?: boolean;      // flag for components with unverified specs
  _review_notes?: string;       // what specifically needs checking
}

export interface BoardPin {
  pin_id: string;             // unique: "D2", "D3", "A0", "3V3", "5V", "GND1"
  label: string;              // what's printed on the board: "2", "3", "A0", "5V"
  capabilities: (
    | "digital"
    | "analog"
    | "pwm"
    | "i2c_sda"
    | "i2c_scl"
    | "spi_mosi"
    | "spi_miso"
    | "spi_sck"
    | "spi_ss"
    | "uart_tx"
    | "uart_rx"
    | "interrupt"
    | "power_5v"
    | "power_3v3"
    | "power_vin"
    | "ground"
  )[];
  voltage: number;             // logic level: 5 or 3.3
  max_current_mA: number;      // max source/sink per pin
  reserved: boolean;           // used by USB, bootloader, onboard LED, etc.
  reserved_reason?: string;    // "Pin 13 has onboard LED — may interfere with external circuits"
}

export interface Board extends Component {
  board_pins: BoardPin[];         // EVERY usable pin on the board
  operating_voltage: number;      // logic level: 5 or 3.3
  input_voltage_range: [number, number];  // [7, 12] for Uno via barrel jack
  max_current_per_pin_mA: number; // 40 for Uno, 40 for ESP32 (but 3.3V)
  max_5v_rail_mA: number;         // 500 via USB for Uno
  max_3v3_rail_mA: number;        // 150 for Uno's onboard regulator, 500 for ESP32
  total_digital_pins: number;
  total_analog_pins: number;
  total_pwm_pins: number;
  has_wifi: boolean;
  has_bluetooth: boolean;
}
