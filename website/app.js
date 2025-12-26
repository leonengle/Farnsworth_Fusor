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
    isAutoModeActive: false
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
    updateStatus('Ready - Waiting for commands', 'blue');
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
    
    elements.setVoltageBtn.addEventListener('click', () => {
        const voltage = appState.voltage;
        if (voltage < 0 || voltage > 28000) {
            updateStatus(`Voltage out of range: ${voltage}V (must be 0-28000V)`, 'red');
            addLogEntry('[ERROR] Voltage out of range');
            return;
        }
        
        updateStatus(`Setting voltage to ${voltage}V...`, 'blue');
        addLogEntry(`[POWER] Setting voltage to ${voltage}V`);
        // TODO: Send command to backend
        console.log(`Set voltage: ${voltage}V`);
    });
}

// Pump Controls
function setupPumpControls() {
    elements.mechPumpSwitch.addEventListener('change', (e) => {
        const isOn = e.target.checked;
        appState.mechPump = isOn;
        elements.mechPumpLabel.textContent = isOn ? 'ON' : 'OFF';
        elements.mechPumpLabel.style.color = isOn ? '#2d8659' : '#b3b3b3';
        
        if (!appState.isAutoModeActive) {
            const power = isOn ? 100 : 0;
            updateStatus(`Setting mechanical pump to ${power}%`, 'blue');
            addLogEntry(`[PUMP] Setting mechanical pump to ${power}%`);
            // TODO: Send command to backend
            console.log(`Mechanical pump: ${power}%`);
        } else {
            e.target.checked = !isOn;
            updateStatus('Cannot control manually while auto mode is active', 'red');
        }
    });
    
    elements.turboPumpSwitch.addEventListener('change', (e) => {
        const isOn = e.target.checked;
        appState.turboPump = isOn;
        elements.turboPumpLabel.textContent = isOn ? 'ON' : 'OFF';
        elements.turboPumpLabel.style.color = isOn ? '#2d8659' : '#b3b3b3';
        
        if (!appState.isAutoModeActive) {
            const power = isOn ? 100 : 0;
            updateStatus(`Setting turbo pump to ${power}%`, 'blue');
            addLogEntry(`[PUMP] Setting turbo pump to ${power}%`);
            // TODO: Send command to backend
            console.log(`Turbo pump: ${power}%`);
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
        
        setButton.addEventListener('click', () => {
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
            // TODO: Send command to backend
            console.log(`Set ${valveKey}: ${value}%`);
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
function startAutoSequence() {
    if (appState.isAutoModeActive) {
        updateStatus('Auto sequence already running', 'yellow');
        return;
    }
    
    appState.isAutoModeActive = true;
    appState.autoState = 'ROUGH_PUMP_DOWN';
    updateAutoState('ROUGH_PUMP_DOWN');
    addAutoLog('[FSM] Auto sequence started');
    updateStatus('Auto sequence started', 'green');
    
    // TODO: Send start command to backend
    console.log('Starting auto sequence');
}

function stopAutoSequence() {
    if (!appState.isAutoModeActive) {
        updateStatus('No active auto sequence', 'yellow');
        return;
    }
    
    appState.isAutoModeActive = false;
    appState.autoState = 'ALL_OFF';
    updateAutoState('ALL_OFF');
    addAutoLog('[FSM] Auto sequence stopped');
    updateStatus('Auto sequence stopped', 'yellow');
    
    // TODO: Send stop command to backend
    console.log('Stopping auto sequence');
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
function emergencyStop() {
    if (confirm('Are you sure you want to execute an EMERGENCY STOP? This will immediately shut down all systems.')) {
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
        
        // TODO: Send emergency stop command to backend
        console.log('EMERGENCY STOP activated');
    }
}

// Data Reading Modal
function openDataReadingModal() {
    elements.dataReadingModal.classList.add('active');
    // TODO: Request current sensor readings
    console.log('Opening data reading window');
}

function closeDataReadingModal() {
    elements.dataReadingModal.classList.remove('active');
}

// Update sensor readings in modal
function updateSensorReadings(data) {
    if (data.rectifierVoltage !== undefined) {
        document.getElementById('rectifierVoltage').textContent = `Rectifier: ${data.rectifierVoltage.toFixed(2)} V`;
    }
    if (data.transformerVoltage !== undefined) {
        document.getElementById('transformerVoltage').textContent = `Transformer: ${data.transformerVoltage.toFixed(2)} V`;
    }
    if (data.vmultiplierVoltage !== undefined) {
        document.getElementById('vmultiplierVoltage').textContent = `V-Multiplier: ${data.vmultiplierVoltage.toFixed(2)} V`;
    }
    if (data.rectifierCurrent !== undefined) {
        document.getElementById('rectifierCurrent').textContent = `Rectifier: ${data.rectifierCurrent.toFixed(3)} A`;
    }
    if (data.vmultiplierCurrent !== undefined) {
        document.getElementById('vmultiplierCurrent').textContent = `V-Multiplier: ${data.vmultiplierCurrent.toFixed(3)} A`;
    }
    if (data.pressure1 !== undefined) {
        document.getElementById('pressureDisplay1').textContent = `TC Gauge 1 [ADC CH0]: ${data.pressure1}`;
    }
    if (data.pressure2 !== undefined) {
        document.getElementById('pressureDisplay2').textContent = `TC Gauge 2 [ADC CH1]: ${data.pressure2}`;
    }
    if (data.pressure3 !== undefined) {
        document.getElementById('pressureDisplay3').textContent = `Manometer 1 [ADC CH2]: ${data.pressure3}`;
    }
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
