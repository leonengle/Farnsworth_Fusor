// API Configuration - Auto-detect based on current host
// In development: uses localhost:5000
// In production: uses same host/port as the web page, or configure via window.API_BASE_URL
const API_BASE_URL = (() => {
    // Allow manual override via global variable (set in HTML)
    if (typeof window !== 'undefined' && window.API_BASE_URL) {
        return window.API_BASE_URL;
    }
    
    // Auto-detect: use same host as current page, but different port for API
    const hostname = window.location.hostname;
    const port = window.location.port || (window.location.protocol === 'https:' ? '443' : '80');
    
    // If running on localhost/127.0.0.1, assume dev mode with API on port 5000
    if (hostname === 'localhost' || hostname === '127.0.0.1' || hostname === '') {
        return 'http://localhost:5000/api';
    }
    
    // In production, assume API is on same host but port 5000, or use proxy
    // Option 1: Same host, different port
    return `${window.location.protocol}//${hostname}:5000/api`;
    
    // Option 2: If using a reverse proxy (uncomment this instead):
    // return '/api';
})();

// Application State
const appState = {
    voltage: 0,
    mechPump: false,
    turboPump: false,
    valves: {
        atm_valve: 0,
        foreline_valve: 0,
        fusor_valve: 0,
        deuterium_valve: 0
    },
    autoState: 'ALL_OFF',
    isAutoModeActive: false,
    connected: false
};

// DOM Elements
const elements = {
    // Tabs
    tabButtons: document.querySelectorAll('.tab-button'),
    tabContents: document.querySelectorAll('.tab-content'),
    
    // Status
    statusLabel: document.getElementById('statusLabel'),
    
    // Voltage Controls
    voltageSlider: document.getElementById('voltageSlider'),
    voltageValue: document.getElementById('voltageValue'),
    setVoltageBtn: document.getElementById('setVoltageBtn'),
    
    // Pump Controls
    mechPumpSwitch: document.getElementById('mechPumpSwitch'),
    mechPumpLabel: document.getElementById('mechPumpLabel'),
    turboPumpSwitch: document.getElementById('turboPumpSwitch'),
    turboPumpLabel: document.getElementById('turboPumpLabel'),
    
    // Valve Controls
    valveControls: document.querySelectorAll('.valve-control'),
    
    // Buttons
    openDataReadingBtn: document.getElementById('openDataReadingBtn'),
    emergencyStopBtn: document.getElementById('emergencyStopBtn'),
    
    // Auto Controls
    autoStartBtn: document.getElementById('autoStartBtn'),
    autoStopBtn: document.getElementById('autoStopBtn'),
    autoStateLabel: document.getElementById('autoStateLabel'),
    autoLogDisplay: document.getElementById('autoLogDisplay'),
    
    // Logs
    targetLogsDisplay: document.getElementById('targetLogsDisplay'),
    clearTargetLogsBtn: document.getElementById('clearTargetLogsBtn'),
    
    // Modal
    dataReadingModal: document.getElementById('dataReadingModal'),
    closeDataReadingBtn: document.getElementById('closeDataReadingBtn')
};

// Initialize Application
function init() {
    setupTabNavigation();
    setupVoltageControls();
    setupPumpControls();
    setupValveControls();
    setupButtons();
    setupAutoControls();
    setupModal();
    setupLogControls();
    startPolling();
    checkConnection();
    updateStatus('Ready - Waiting for commands', 'blue');
}

// API Helper Functions
async function apiCall(endpoint, method = 'GET', data = null) {
    try {
        const options = {
            method: method,
            headers: {
                'Content-Type': 'application/json'
            }
        };
        
        if (data && method !== 'GET') {
            options.body = JSON.stringify(data);
        }
        
        const response = await fetch(`${API_BASE_URL}${endpoint}`, options);
        const result = await response.json();
        return result;
    } catch (error) {
        console.error(`API call failed: ${error}`);
        return { success: false, error: error.message };
    }
}

// Connection and Status Polling
async function checkConnection() {
    const status = await apiCall('/status');
    if (status.connected !== undefined) {
        appState.connected = status.connected;
        appState.autoState = status.auto_state || 'ALL_OFF';
        appState.isAutoModeActive = status.auto_mode_active || false;
        
        updateAutoState(appState.autoState);
        
        if (status.connected) {
            updateStatus('Connected to target', 'green');
        } else {
            updateStatus('Disconnected from target', 'red');
        }
    }
}

function startPolling() {
    // Poll status every 2 seconds
    setInterval(checkConnection, 2000);
    
    // Poll telemetry every 1 second
    setInterval(pollTelemetry, 1000);
    
    // Poll logs every 3 seconds
    setInterval(pollLogs, 3000);
}

async function pollTelemetry() {
    const result = await apiCall('/telemetry');
    if (result.success && result.telemetry) {
        updateSensorReadings(result.telemetry);
    }
}

async function pollLogs() {
    const result = await apiCall('/logs?limit=50');
    if (result.success && result.logs) {
        elements.targetLogsDisplay.value = result.logs.join('\n');
        elements.targetLogsDisplay.scrollTop = elements.targetLogsDisplay.scrollHeight;
    }
}

// Tab Navigation
function setupTabNavigation() {
    elements.tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const tabName = button.getAttribute('data-tab');
            
            // Remove active class from all tabs
            elements.tabButtons.forEach(btn => btn.classList.remove('active'));
            elements.tabContents.forEach(content => content.classList.remove('active'));
            
            // Add active class to selected tab
            button.classList.add('active');
            document.getElementById(`${tabName}Tab`).classList.add('active');
        });
    });
}

// Voltage Controls
function setupVoltageControls() {
    elements.voltageSlider.addEventListener('input', (e) => {
        const value = parseInt(e.target.value);
        appState.voltage = value;
        elements.voltageValue.textContent = `${value} V`;
    });
    
    elements.setVoltageBtn.addEventListener('click', async () => {
        const voltage = appState.voltage;
        if (voltage < 0 || voltage > 28000) {
            updateStatus(`Voltage out of range: ${voltage}V (must be 0-28000V)`, 'red');
            addLogEntry('[ERROR] Voltage out of range');
            return;
        }
        
        updateStatus(`Setting voltage to ${voltage}V...`, 'blue');
        addLogEntry(`[POWER] Setting voltage to ${voltage}V`);
        
        const result = await apiCall('/voltage/set', 'POST', { voltage });
        if (result.success) {
            updateStatus(`Voltage set to ${voltage}V`, 'green');
            addAutoLog(`[POWER] Voltage set to ${voltage}V`);
        } else {
            updateStatus(`Failed to set voltage: ${result.error}`, 'red');
            addAutoLog(`[ERROR] Failed to set voltage: ${result.error}`);
        }
    });
}

// Pump Controls
function setupPumpControls() {
    elements.mechPumpSwitch.addEventListener('change', async (e) => {
        const isOn = e.target.checked;
        appState.mechPump = isOn;
        elements.mechPumpLabel.textContent = isOn ? 'ON' : 'OFF';
        elements.mechPumpLabel.style.color = isOn ? '#2d8659' : '#b3b3b3';
        
        if (!appState.isAutoModeActive) {
            const power = isOn ? 100 : 0;
            updateStatus(`Setting mechanical pump to ${power}%`, 'blue');
            addLogEntry(`[PUMP] Setting mechanical pump to ${power}%`);
            
            const result = await apiCall('/pump/mechanical', 'POST', { power });
            if (result.success) {
                updateStatus(`Mechanical pump set to ${power}%`, 'green');
            } else {
                updateStatus(`Failed: ${result.error}`, 'red');
                e.target.checked = !isOn; // Revert switch
            }
        } else {
            e.target.checked = !isOn;
            updateStatus('Cannot control manually while auto mode is active', 'red');
        }
    });
    
    elements.turboPumpSwitch.addEventListener('change', async (e) => {
        const isOn = e.target.checked;
        appState.turboPump = isOn;
        elements.turboPumpLabel.textContent = isOn ? 'ON' : 'OFF';
        elements.turboPumpLabel.style.color = isOn ? '#2d8659' : '#b3b3b3';
        
        if (!appState.isAutoModeActive) {
            const power = isOn ? 100 : 0;
            updateStatus(`Setting turbo pump to ${power}%`, 'blue');
            addLogEntry(`[PUMP] Setting turbo pump to ${power}%`);
            
            const result = await apiCall('/pump/turbo', 'POST', { power });
            if (result.success) {
                updateStatus(`Turbo pump set to ${power}%`, 'green');
            } else {
                updateStatus(`Failed: ${result.error}`, 'red');
                e.target.checked = !isOn; // Revert switch
            }
        } else {
            e.target.checked = !isOn;
            updateStatus('Cannot control manually while auto mode is active', 'red');
        }
    });
}

// Valve Controls
function setupValveControls() {
    elements.valveControls.forEach((control) => {
        const slider = control.querySelector('.valve-slider');
        const valueLabel = control.querySelector('.valve-value');
        const setButton = control.querySelector('[data-valve-set]');
        const valveKey = setButton ? setButton.getAttribute('data-valve-set') : control.getAttribute('data-valve');
        
        if (!valveKey || !slider || !valueLabel || !setButton) {
            return;
        }
        
        // Initialize state
        if (!appState.valves[valveKey]) {
            appState.valves[valveKey] = 0;
        }
        
        slider.addEventListener('input', (e) => {
            const value = parseInt(e.target.value);
            valueLabel.textContent = `${value}%`;
            appState.valves[valveKey] = value;
        });
        
        setButton.addEventListener('click', async () => {
            const value = parseInt(slider.value);
            
            if (appState.isAutoModeActive) {
                updateStatus('Cannot control manually while auto mode is active', 'red');
                return;
            }
            
            if (value < 0 || value > 100) {
                updateStatus(`Invalid valve value: ${value} (must be 0-100)`, 'red');
                return;
            }
            
            appState.valves[valveKey] = value;
            updateStatus(`Setting ${valveKey} to ${value}%...`, 'blue');
            addLogEntry(`[VALVE] Setting ${valveKey} to ${value}%`);
            
            const result = await apiCall('/valve/set', 'POST', { valve: valveKey, position: value });
            if (result.success) {
                updateStatus(`${valveKey} set to ${value}%`, 'green');
            } else {
                updateStatus(`Failed: ${result.error}`, 'red');
            }
        });
    });
}

// Buttons
function setupButtons() {
    elements.openDataReadingBtn.addEventListener('click', () => {
        openDataReadingModal();
    });
    
    elements.emergencyStopBtn.addEventListener('click', () => {
        emergencyStop();
    });
}

// Auto Controls
function setupAutoControls() {
    elements.autoStartBtn.addEventListener('click', () => {
        startAutoSequence();
    });
    
    elements.autoStopBtn.addEventListener('click', () => {
        stopAutoSequence();
    });
}

// Modal
function setupModal() {
    elements.closeDataReadingBtn.addEventListener('click', () => {
        closeDataReadingModal();
    });
    
    // Close modal when clicking outside
    elements.dataReadingModal.addEventListener('click', (e) => {
        if (e.target === elements.dataReadingModal) {
            closeDataReadingModal();
        }
    });
    
    // Close modal with ESC key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && elements.dataReadingModal.classList.contains('active')) {
            closeDataReadingModal();
        }
    });
}

// Log Controls
function setupLogControls() {
    elements.clearTargetLogsBtn.addEventListener('click', () => {
        elements.targetLogsDisplay.value = '[Target Logs] Logs cleared.\n';
    });
}

// Status Updates
function updateStatus(message, color = 'blue') {
    elements.statusLabel.textContent = message;
    const colorMap = {
        'blue': '#4a9eff',
        'green': '#2d8659',
        'red': '#d73027',
        'yellow': '#f0ad4e',
        'white': '#ffffff'
    };
    elements.statusLabel.style.color = colorMap[color] || colorMap['blue'];
}

// Add Log Entry (for data display - would be in separate window in original)
function addLogEntry(message) {
    const timestamp = new Date().toLocaleTimeString();
    // This would go to a data log window in the original
    console.log(`${timestamp} - ${message}`);
}

// Auto Sequence Functions
async function startAutoSequence() {
    if (appState.isAutoModeActive) {
        updateStatus('Auto sequence already running', 'yellow');
        return;
    }
    
    const result = await apiCall('/auto/start', 'POST');
    if (result.success) {
        appState.isAutoModeActive = true;
        appState.autoState = result.state;
        updateAutoState(result.state);
        addAutoLog('[FSM] Auto sequence started');
        updateStatus('Auto sequence started', 'green');
    } else {
        updateStatus(`Failed to start auto sequence: ${result.error}`, 'red');
    }
}

async function stopAutoSequence() {
    const result = await apiCall('/auto/stop', 'POST');
    if (result.success) {
        appState.isAutoModeActive = false;
        appState.autoState = result.state;
        updateAutoState(result.state);
        addAutoLog('[FSM] Auto sequence stopped');
        updateStatus('Auto sequence stopped', 'yellow');
    } else {
        updateStatus(`Failed to stop auto sequence: ${result.error}`, 'red');
    }
}

function updateAutoState(state) {
    const stateNames = {
        'ALL_OFF': 'ALL_OFF',
        'ROUGH_PUMP_DOWN': 'ROUGH_PUMP_DOWN',
        'RP_DOWN_TURBO': 'RP_DOWN_TURBO',
        'TURBO_PUMP_DOWN': 'TURBO_PUMP_DOWN',
        'TP_DOWN_MAIN': 'TP_DOWN_MAIN',
        'SETTLE_STEADY_PRESSURE': 'SETTLE_STEADY_PRESSURE',
        'SETTLING_10KV': 'SETTLING_10KV',
        'NOMINAL_27KV': 'NOMINAL_27KV',
        'DEENERGIZING': 'DEENERGIZING',
        'CLOSING_MAIN': 'CLOSING_MAIN',
        'VENTING_FORELINE': 'VENTING_FORELINE',
        'VENTING_ATM': 'VENTING_ATM'
    };
    
    appState.autoState = state;
    elements.autoStateLabel.textContent = `Current State: ${stateNames[state] || state}`;
}

function addAutoLog(message) {
    const timestamp = new Date().toLocaleTimeString();
    const logEntry = `[${timestamp}] ${message}\n`;
    elements.autoLogDisplay.value += logEntry;
    elements.autoLogDisplay.scrollTop = elements.autoLogDisplay.scrollHeight;
}

function addTargetLog(message) {
    const timestamp = new Date().toLocaleTimeString();
    const logEntry = `[${timestamp}] ${message}\n`;
    elements.targetLogsDisplay.value += logEntry;
    elements.targetLogsDisplay.scrollTop = elements.targetLogsDisplay.scrollHeight;
    
    // Limit log size
    const lines = elements.targetLogsDisplay.value.split('\n');
    if (lines.length > 1000) {
        elements.targetLogsDisplay.value = lines.slice(lines.length - 1000).join('\n');
    }
}

// Emergency Stop
async function emergencyStop() {
    if (confirm('Are you sure you want to execute an EMERGENCY STOP? This will immediately shut down all systems.')) {
        const result = await apiCall('/emergency/stop', 'POST');
        if (result.success) {
        appState.isAutoModeActive = false;
        appState.autoState = 'ALL_OFF';
        updateAutoState('ALL_OFF');
        
        // Reset all controls
        appState.voltage = 0;
        elements.voltageSlider.value = 0;
        elements.voltageValue.textContent = '0 V';
        
        appState.mechPump = false;
        elements.mechPumpSwitch.checked = false;
        elements.mechPumpLabel.textContent = 'OFF';
        
        appState.turboPump = false;
        elements.turboPumpSwitch.checked = false;
        elements.turboPumpLabel.textContent = 'OFF';
        
        Object.keys(appState.valves).forEach(key => {
            appState.valves[key] = 0;
        });
        elements.valveControls.forEach(control => {
            const slider = control.querySelector('.valve-slider');
            const valueLabel = control.querySelector('.valve-value');
            if (slider) slider.value = 0;
            if (valueLabel) valueLabel.textContent = '0%';
        });
        
            updateStatus('EMERGENCY STOP ACTIVATED', 'red');
            addAutoLog('[FSM] EMERGENCY STOP activated - All systems shut down');
            addTargetLog('[EMERGENCY] Emergency stop activated');
        } else {
            updateStatus(`Failed to execute emergency stop: ${result.error}`, 'red');
        }
    }
}

// Data Reading Modal
async function openDataReadingModal() {
    elements.dataReadingModal.classList.add('active');
    
    // Request current sensor readings
    const result = await apiCall('/sensors/read', 'GET');
    if (result.success && result.sensors) {
        parseSensorData(result.sensors);
    }
}

function parseSensorData(sensorData) {
    // Parse voltage readings
    for (const [cmd, response] of Object.entries(sensorData)) {
        if (cmd.includes('NODE_') && cmd.includes('_VOLTAGE')) {
            const match = response.match(/NODE_(\d+)_VOLTAGE:([\d.]+)/);
            if (match) {
                const nodeId = parseInt(match[1]);
                const voltage = parseFloat(match[2]);
                if (nodeId === 1) {
                    document.getElementById('rectifierVoltage').textContent = `Rectifier: ${voltage.toFixed(2)} V`;
                } else if (nodeId === 2) {
                    document.getElementById('transformerVoltage').textContent = `Transformer: ${voltage.toFixed(2)} V`;
                } else if (nodeId === 3) {
                    document.getElementById('vmultiplierVoltage').textContent = `V-Multiplier: ${voltage.toFixed(2)} V`;
                }
            }
        } else if (cmd.includes('NODE_') && cmd.includes('_CURRENT')) {
            const match = response.match(/NODE_(\d+)_CURRENT:([\d.]+)/);
            if (match) {
                const nodeId = parseInt(match[1]);
                const current = parseFloat(match[2]);
                if (nodeId === 1) {
                    document.getElementById('rectifierCurrent').textContent = `Rectifier: ${current.toFixed(3)} A`;
                } else if (nodeId === 3) {
                    document.getElementById('vmultiplierCurrent').textContent = `V-Multiplier: ${current.toFixed(3)} A`;
                }
            }
        } else if (cmd.includes('ADC')) {
            // Parse ADC data
            const parts = response.split('|');
            for (const part of parts) {
                if (part.includes('ADC_CH0')) {
                    const value = part.split(':')[1];
                    document.getElementById('pressureDisplay1').textContent = `TC Gauge 1 [ADC CH0]: ${value}`;
                } else if (part.includes('ADC_CH1')) {
                    const value = part.split(':')[1];
                    document.getElementById('pressureDisplay2').textContent = `TC Gauge 2 [ADC CH1]: ${value}`;
                } else if (part.includes('ADC_CH2')) {
                    const value = part.split(':')[1];
                    document.getElementById('pressureDisplay3').textContent = `Manometer 1 [ADC CH2]: ${value}`;
                }
            }
        }
    }
}

function closeDataReadingModal() {
    elements.dataReadingModal.classList.remove('active');
}

// Update sensor readings from telemetry
function updateSensorReadings(telemetry) {
    // Update from telemetry dict (parsed UDP data)
    if (telemetry.ADC_CH0) {
        document.getElementById('pressureDisplay1').textContent = `TC Gauge 1 [ADC CH0]: ${telemetry.ADC_CH0}`;
    }
    if (telemetry.ADC_CH1) {
        document.getElementById('pressureDisplay2').textContent = `TC Gauge 2 [ADC CH1]: ${telemetry.ADC_CH1}`;
    }
    if (telemetry.ADC_CH2) {
        document.getElementById('pressureDisplay3').textContent = `Manometer 1 [ADC CH2]: ${telemetry.ADC_CH2}`;
    }
    // Update other sensor readings as they come in
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}

// Export functions for potential use by backend integration
window.fusorControl = {
    updateStatus,
    addAutoLog,
    addTargetLog,
    updateAutoState,
    updateSensorReadings,
    appState
};
