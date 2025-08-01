dataDownloadCodes = [
    {
        "deviceName": "Dive Computer",
        "deviceCategoryCode": "DIVE_COMPUTER",
        "locationCode": "CBYDS",
        "possibleDataProducts": [
            {
                "dataProduct": "Log File",
                "dataProductCode": "LF",
                "availableExtensions": ["txt"],
            },
            {
                "dataProduct": "Manual Scalar QAQC",
                "dataProductCode": "MSQAQCR",
                "availableExtensions": ["qaqc"],
            },
            {
                "dataProduct": "Time Series Scalar Data",
                "dataProductCode": "TSSD",
                "availableExtensions": ["csv", "json", "mat", "txt"],
            },
            {
                "dataProduct": "Time Series Scalar Plot",
                "dataProductCode": "TSSP",
                "availableExtensions": ["pdf", "png"],
            },
        ],
    },
    {
        "deviceName": "Navigation",
        "deviceCategoryCode": "NAV",
        "locationCode": "CBYDS",
        "possibleDataProducts": [
            {
                "dataProduct": "Log File",
                "dataProductCode": "LF",
                "availableExtensions": ["txt"],
            },
            {
                "dataProduct": "Manual Scalar QAQC",
                "dataProductCode": "MSQAQCR",
                "availableExtensions": ["qaqc"],
            },
            {
                "dataProduct": "Time Series Scalar Data",
                "dataProductCode": "TSSD",
                "availableExtensions": ["csv", "json", "mat", "txt"],
            },
            {
                "dataProduct": "Time Series Scalar Plot",
                "dataProductCode": "TSSP",
                "availableExtensions": ["pdf", "png"],
            },
            {
                "dataProduct": "Navigation Data",
                "dataProductCode": "ND",
                "availableExtensions": ["zip"],
            },
        ],
    },
    {
        "deviceName": "Remotely Operated Vehicle Camera",
        "deviceCategoryCode": "ROV_CAMERA",
        "locationCode": "CBYDS",
        "possibleDataProducts": [
            {
                "dataProduct": "MP4 Video",
                "dataProductCode": "MP4V",
                "availableExtensions": ["mp4"],
            }
        ],
    },
    {
        "deviceName": "Acoustic Receiver",
        "deviceCategoryCode": "ACOUSTICRECEIVER",
        "locationCode": "CBYIP",
        "possibleDataProducts": [
            {
                "dataProduct": "Log File",
                "dataProductCode": "LF",
                "availableExtensions": ["txt"],
            },
            {
                "dataProduct": "Vemco Raw Files",
                "dataProductCode": "VRF",
                "availableExtensions": ["csv", "vrl"],
            },
        ],
    },
    {
        "deviceName": "Acoustic Doppler Current Profiler 1200 kHz",
        "deviceCategoryCode": "ADCP1200KHZ",
        "locationCode": "CBYIP",
        "possibleDataProducts": [
            {
                "dataProduct": "Log File",
                "dataProductCode": "LF",
                "availableExtensions": ["txt"],
            },
            {
                "dataProduct": "Manual Scalar QAQC",
                "dataProductCode": "MSQAQCR",
                "availableExtensions": ["qaqc"],
            },
            {
                "dataProduct": "RDI ADCP Time Series",
                "dataProductCode": "RADCPTS",
                "availableExtensions": ["pdf", "mat", "nc"],
            },
            {
                "dataProduct": "RDI Daily Current Plot",
                "dataProductCode": "RDCUP",
                "availableExtensions": ["png"],
            },
            {
                "dataProduct": "RDI Daily Intensity Plot",
                "dataProductCode": "RDIP",
                "availableExtensions": ["pdf", "png"],
            },
            {
                "dataProduct": "Time Series Scalar Data",
                "dataProductCode": "TSSD",
                "availableExtensions": ["csv", "json", "mat", "txt"],
            },
            {
                "dataProduct": "Time Series Scalar Plot",
                "dataProductCode": "TSSP",
                "availableExtensions": ["pdf", "png"],
            },
        ],
    },
    {
        "deviceName": "Camera Lights",
        "deviceCategoryCode": "CAMLIGHTS",
        "locationCode": "CBYIP",
        "possibleDataProducts": [
            {
                "dataProduct": "Log File",
                "dataProductCode": "LF",
                "availableExtensions": ["txt"],
            },
            {
                "dataProduct": "Manual Scalar QAQC",
                "dataProductCode": "MSQAQCR",
                "availableExtensions": ["qaqc"],
            },
            {
                "dataProduct": "Time Series Staircase Plot",
                "dataProductCode": "TSSCP",
                "availableExtensions": ["pdf", "png"],
            },
            {
                "dataProduct": "Time Series Scalar Data",
                "dataProductCode": "TSSD",
                "availableExtensions": ["csv", "json", "mat", "txt"],
            },
            {
                "dataProduct": "Time Series Scalar Plot",
                "dataProductCode": "TSSP",
                "availableExtensions": ["pdf", "png"],
            },
        ],
    },
    {
        "deviceName": "Conductivity Temperature Depth",
        "deviceCategoryCode": "CTD",
        "locationCode": "CBYIP",
        "possibleDataProducts": [
            {
                "dataProduct": "Annotation File",
                "dataProductCode": "AF",
                "availableExtensions": ["mat"],
            },
            {
                "dataProduct": "Cast Scalar Profile Plot and Data",
                "dataProductCode": "CSPPD",
                "availableExtensions": ["png", "nc"],
            },
            {
                "dataProduct": "Log File",
                "dataProductCode": "LF",
                "availableExtensions": ["txt"],
            },
            {
                "dataProduct": "Manual Scalar QAQC",
                "dataProductCode": "MSQAQCR",
                "availableExtensions": ["qaqc"],
            },
            {
                "dataProduct": "Sea-Bird CTD Raw Files",
                "dataProductCode": "SBCTDRF",
                "availableExtensions": ["pdf"],
            },
            {
                "dataProduct": "Time Series Staircase Plot",
                "dataProductCode": "TSSCP",
                "availableExtensions": ["pdf"],
            },
            {
                "dataProduct": "Time Series Scalar Plot",
                "dataProductCode": "TSSP",
                "availableExtensions": ["pdf", "png"],
            },
            {
                "dataProduct": "Time Series Scalar Data",
                "dataProductCode": "TSSD",
                "availableExtensions": ["csv", "json", "mat", "txt"],
            },
            {
                "dataProduct": "Time Series Scalar Profile Plot and Gridded Data",
                "dataProductCode": "TSSPPGD",
                "availableExtensions": ["pdf", "png", "mat", "nc"],
            },
        ],
    },
    {
        "deviceName": "Fluorometer Turbidity",
        "deviceCategoryCode": "FLNTU",
        "locationCode": "CBYIP",
        "possibleDataProducts": [
            {
                "dataProduct": "Cast Scalar Profile Plot and Data",
                "dataProductCode": "CSPPD",
                "availableExtensions": ["pdf", "png", "nc"],
            },
            {
                "dataProduct": "Log File",
                "dataProductCode": "LF",
                "availableExtensions": ["txt"],
            },
            {
                "dataProduct": "Manual Scalar QAQC",
                "dataProductCode": "MSQAQCR",
                "availableExtensions": ["qaqc"],
            },
            {
                "dataProduct": "Time Series Scalar Data",
                "dataProductCode": "TSSD",
                "availableExtensions": ["csv", "json", "mat", "nc", "txt"],
            },
            {
                "dataProduct": "Time Series Scalar Plot",
                "dataProductCode": "TSSP",
                "availableExtensions": ["pdf", "png"],
            },
            {
                "dataProduct": "Time Series Scalar Profile Plot and Gridded Data",
                "dataProductCode": "TSSPPGD",
                "availableExtensions": ["pdf", "png", "mat", "nc"],
            },
        ],
    },
    {
        "deviceName": "Fluorometer",
        "deviceCategoryCode": "FLUOROMETER",
        "locationCode": "CBYIP",
        "possibleDataProducts": [
            {
                "dataProduct": "Cast Scalar Profile Plot and Data",
                "dataProductCode": "CSPPD",
                "availableExtensions": ["pdf", "png", "mat", "nc"],
            },
            {
                "dataProduct": "Log File",
                "dataProductCode": "LF",
                "availableExtensions": ["txt"],
            },
            {
                "dataProduct": "Manual Scalar QAQC",
                "dataProductCode": "MSQAQCR",
                "availableExtensions": ["qaqc"],
            },
            {
                "dataProduct": "Time Series Scalar Data",
                "dataProductCode": "TSSD",
                "availableExtensions": ["csv", "json", "mat", "nc", "txt"],
            },
            {
                "dataProduct": "Time Series Scalar Plot",
                "dataProductCode": "TSSP",
                "availableExtensions": ["pdf", "png"],
            },
            {
                "dataProduct": "Time Series Scalar Profile Plot and Gridded Data",
                "dataProductCode": "TSSPPGD",
                "availableExtensions": ["pdf", "png", "mat", "nc"],
            },
        ],
    },
    {
        "deviceName": "Hydrophone",
        "deviceCategoryCode": "HYDROPHONE",
        "locationCode": "CBYIP",
        "possibleDataProducts": [
            {
                "dataProduct": "Audio Data",
                "dataProductCode": "AD",
                "availableExtensions": ["mp3", "flac", "wav"],
            },
            {
                "dataProduct": "Annotation File",
                "dataProductCode": "AF",
                "availableExtensions": ["an"],
            },
            {
                "dataProduct": "Hydrophone Spectral Data",
                "dataProductCode": "HSD",
                "availableExtensions": ["pdf", "png", "fft", "mat"],
            },
            {
                "dataProduct": "Hydrophone Spectral Probability Density",
                "dataProductCode": "HSPD",
                "availableExtensions": ["pdf", "txt"],
            },
            {
                "dataProduct": "Manual Scalar QAQC",
                "dataProductCode": "MSQAQCR",
                "availableExtensions": ["qaqc"],
            },
            {
                "dataProduct": "Spectrogram for Hydrophone Viewer",
                "dataProductCode": "SHV",
                "availableExtensions": ["png"],
            },
            {
                "dataProduct": "Time Series Staircase Plot",
                "dataProductCode": "TSSCP",
                "availableExtensions": ["pdf", "png"],
            },
            {
                "dataProduct": "Time Series Scalar Data",
                "dataProductCode": "TSSD",
                "availableExtensions": ["csv", "json", "mat", "txt"],
            },
            {
                "dataProduct": "Time Series Scalar Plot",
                "dataProductCode": "TSSP",
                "availableExtensions": ["pdf", "png"],
            },
        ],
    },
    {
        "deviceName": "Ice Profiler",
        "deviceCategoryCode": "ICEPROFILER",
        "locationCode": "CBYIP",
        "possibleDataProducts": [
            {
                "dataProduct": "Log File",
                "dataProductCode": "LF",
                "availableExtensions": ["txt"],
            },
            {
                "dataProduct": "Manual Scalar QAQC",
                "dataProductCode": "MSQAQCR",
                "availableExtensions": ["qaqc"],
            },
            {
                "dataProduct": "Time Series Scalar Data",
                "dataProductCode": "TSSD",
                "availableExtensions": ["csv", "json", "mat", "txt"],
            },
            {
                "dataProduct": "Time Series Scalar Plot",
                "dataProductCode": "TSSP",
                "availableExtensions": ["pdf", "png"],
            },
        ],
    },
    {
        "deviceName": "Nitrate Sensor",
        "deviceCategoryCode": "NITRATESENSOR",
        "locationCode": "CBYIP",
        "possibleDataProducts": [
            {
                "dataProduct": "Cast Scalar Profile Plot and Data",
                "dataProductCode": "CSPPD",
                "availableExtensions": ["pdf", "mat", "png", "nc"],
            },
            {
                "dataProduct": "Log File",
                "dataProductCode": "LF",
                "availableExtensions": ["txt", "log"],
            },
            {
                "dataProduct": "Manual Scalar QAQC",
                "dataProductCode": "MSQAQCR",
                "availableExtensions": ["qaqc"],
            },
            {
                "dataProduct": "Satlantic ISUS Time Series",
                "dataProductCode": "SISUSTS",
                "availableExtensions": ["raw"],
            },
            {
                "dataProduct": "Time Series Scalar Data",
                "dataProductCode": "TSSD",
                "availableExtensions": ["csv", "json", "nc", "txt"],
            },
            {
                "dataProduct": "Time Series Scalar Plot",
                "dataProductCode": "TSSP",
                "availableExtensions": ["pdf", "png"],
            },
            {
                "dataProduct": "Time Series Scalar Profile Plot and Gridded Data",
                "dataProductCode": "TSSPPGD",
                "availableExtensions": ["pdf", "mat", "png", "nc"],
            },
        ],
    },
    {
        "deviceName": "Oxygen Sensor",
        "deviceCategoryCode": "OXYSENSOR",
        "locationCode": "CBYIP",
        "possibleDataProducts": [
            {
                "dataProduct": "Cast Scalar Profile Plot and Data",
                "dataProductCode": "CSPPD",
                "availableExtensions": ["pdf", "mat", "png", "nc"],
            },
            {
                "dataProduct": "Log File",
                "dataProductCode": "LF",
                "availableExtensions": ["txt"],
            },
            {
                "dataProduct": "Manual Scalar QAQC",
                "dataProductCode": "MSQAQCR",
                "availableExtensions": ["qaqc"],
            },
            {
                "dataProduct": "Time Series Scalar Data",
                "dataProductCode": "TSSD",
                "availableExtensions": ["csv", "json", "mat", "nc", "txt"],
            },
            {
                "dataProduct": "Time Series Scalar Plot",
                "dataProductCode": "TSSP",
                "availableExtensions": ["pdf", "png"],
            },
            {
                "dataProduct": "Time Series Scalar Profile Plot and Gridded Data",
                "dataProductCode": "TSSPPGD",
                "availableExtensions": ["pdf", "mat", "png", "nc"],
            },
        ],
    },
    {
        "deviceName": "pH Sensor",
        "deviceCategoryCode": "PHSENSOR",
        "locationCode": "CBYIP",
        "possibleDataProducts": [
            {
                "dataProduct": "Log File",
                "dataProductCode": "LF",
                "availableExtensions": ["txt"],
            },
            {
                "dataProduct": "Manual Scalar QAQC",
                "dataProductCode": "MSQAQCR",
                "availableExtensions": ["qaqc"],
            },
            {
                "dataProduct": "Time Series Scalar Data",
                "dataProductCode": "TSSD",
                "availableExtensions": ["csv", "json", "mat", "nc", "txt"],
            },
            {
                "dataProduct": "Time Series Scalar Plot",
                "dataProductCode": "TSSP",
                "availableExtensions": ["pdf", "png"],
            },
        ],
    },
    {
        "deviceName": "Plankton Sampler",
        "deviceCategoryCode": "PLANKTONSAMPLER",
        "locationCode": "CBYIP",
        "possibleDataProducts": [
            {
                "dataProduct": "Log File",
                "dataProductCode": "LF",
                "availableExtensions": ["txt"],
            },
            {
                "dataProduct": "Manual Scalar QAQC",
                "dataProductCode": "MSQAQCR",
                "availableExtensions": ["qaqc"],
            },
            {
                "dataProduct": "Time Series Staircase Plot",
                "dataProductCode": "TSSCP",
                "availableExtensions": ["pdf", "png"],
            },
            {
                "dataProduct": "Time Series Scalar Data",
                "dataProductCode": "TSSD",
                "availableExtensions": ["csv", "json", "mat", "txt"],
            },
            {
                "dataProduct": "Time Series Scalar Plot",
                "dataProductCode": "TSSP",
                "availableExtensions": ["pdf", "png"],
            },
        ],
    },
    {
        "deviceName": "Radiometer",
        "deviceCategoryCode": "RADIOMETER",
        "locationCode": "CBYIP",
        "possibleDataProducts": [
            {
                "dataProduct": "Log File",
                "dataProductCode": "LF",
                "availableExtensions": ["txt"],
            },
            {
                "dataProduct": "Manual Scalar QAQC",
                "dataProductCode": "MSQAQCR",
                "availableExtensions": ["qaqc"],
            },
            {
                "dataProduct": "Time Series Scalar Data",
                "dataProductCode": "TSSD",
                "availableExtensions": ["csv", "json", "mat", "txt"],
            },
            {
                "dataProduct": "Time Series Scalar Plot",
                "dataProductCode": "TSSP",
                "availableExtensions": ["pdf", "png"],
            },
        ],
    },
    {
        "deviceName": "Turbidity Meter",
        "deviceCategoryCode": "TURBIDITYMETER",
        "locationCode": "CBYIP",
        "possibleDataProducts": [
            {
                "dataProduct": "Cast Scalar Profile Plot and Data",
                "dataProductCode": "CSPPD",
                "availableExtensions": ["pdf", "png"],
            },
            {
                "dataProduct": "Log File",
                "dataProductCode": "LF",
                "availableExtensions": ["txt"],
            },
            {
                "dataProduct": "Manual Scalar QAQC",
                "dataProductCode": "MSQAQCR",
                "availableExtensions": ["qaqc"],
            },
            {
                "dataProduct": "Time Series Scalar Data",
                "dataProductCode": "TSSD",
                "availableExtensions": ["csv", "json", "mat", "txt"],
            },
            {
                "dataProduct": "Time Series Scalar Plot",
                "dataProductCode": "TSSP",
                "availableExtensions": ["pdf", "png"],
            },
        ],
    },
    {
        "deviceName": "Video Camera",
        "deviceCategoryCode": "VIDEOCAM",
        "locationCode": "CBYIP",
        "possibleDataProducts": [
            {
                "dataProduct": "Annotation File",
                "dataProductCode": "AF",
                "availableExtensions": ["an"],
            },
            {
                "dataProduct": "ASF Video",
                "dataProductCode": "ASFV",
                "availableExtensions": ["asf"],
            },
            {
                "dataProduct": "JPG File",
                "dataProductCode": "JPGF",
                "availableExtensions": ["jpg"],
            },
            {
                "dataProduct": "Log File",
                "dataProductCode": "LF",
                "availableExtensions": ["txt"],
            },
            {
                "dataProduct": "MP4 Video",
                "dataProductCode": "MP4V",
                "availableExtensions": ["mp4"],
            },
            {
                "dataProduct": "Manual Scalar QAQC",
                "dataProductCode": "MSQAQCR",
                "availableExtensions": ["qaqc"],
            },
            {
                "dataProduct": "Time Series Staircase Plot",
                "dataProductCode": "TSSCP",
                "availableExtensions": ["pdf", "png"],
            },
            {
                "dataProduct": "Time Series Scalar Data",
                "dataProductCode": "TSSD",
                "availableExtensions": ["csv", "json", "mat", "txt"],
            },
            {
                "dataProduct": "Time Series Scalar Plot",
                "dataProductCode": "TSSP",
                "availableExtensions": ["pdf", "png"],
            },
            {
                "dataProduct": "Video QAQC Results",
                "dataProductCode": "VQAQCR",
                "availableExtensions": ["an"],
            },
            {
                "dataProduct": "Video QAQCM Training Set Black",
                "dataProductCode": "VQAQCTSB",
                "availableExtensions": ["zip"],
            },
            {
                "dataProduct": "Video QAQC Training Set Focus",
                "dataProductCode": "VQAQCTSF",
                "availableExtensions": ["zip"],
            },
            {
                "dataProduct": "Video QAQC Training Set Shift Detect",
                "dataProductCode": "VQAQCTSSD",
                "availableExtensions": ["zip"],
            },
        ],
    },
    {
        "deviceName": "Water Quality Monitor",
        "deviceCategoryCode": "WETLABS_WQM",
        "locationCode": "CBYIP",
        "possibleDataProducts": [
            {
                "dataProduct": "Log File",
                "dataProductCode": "LF",
                "availableExtensions": ["txt"],
            },
            {
                "dataProduct": "Manual Scalar QAQC",
                "dataProductCode": "MSQAQCR",
                "availableExtensions": ["qaqc"],
            },
            {
                "dataProduct": "Time Series Scalar Data",
                "dataProductCode": "TSSD",
                "availableExtensions": ["csv", "json", "mat", "txt"],
            },
            {
                "dataProduct": "Time Series Scalar Plot",
                "dataProductCode": "TSSP",
                "availableExtensions": ["pdf", "png"],
            },
        ],
    },
    {
        "deviceName": "Internal Device Monitor",
        "deviceCategoryCode": "INTERNAL_DEVICE_MONITOR",
        "locationCode": "CBYIU",
        "possibleDataProducts": [
            {
                "dataProduct": "Log File",
                "dataProductCode": "LF",
                "availableExtensions": ["txt"],
            },
            {
                "dataProduct": "Manual Scalar QAQC",
                "dataProductCode": "MSQAQCR",
                "availableExtensions": ["qaqc"],
            },
            {
                "dataProduct": "Time Series Scalar Data",
                "dataProductCode": "TSSD",
                "availableExtensions": ["csv", "json", "mat", "txt"],
            },
            {
                "dataProduct": "Time Series Scalar Plot",
                "dataProductCode": "TSSP",
                "availableExtensions": ["pdf", "png"],
            },
        ],
    },
    {
        "deviceName": "Orientation Instrument",
        "deviceCategoryCode": "ORIENTATION",
        "locationCode": "CBYIU",
        "possibleDataProducts": [
            {
                "dataProduct": "Log File",
                "dataProductCode": "LF",
                "availableExtensions": ["txt"],
            },
            {
                "dataProduct": "Manual Scalar QAQC",
                "dataProductCode": "MSQAQCR",
                "availableExtensions": ["qaqc"],
            },
            {
                "dataProduct": "Time Series Scalar Data",
                "dataProductCode": "TSSD",
                "availableExtensions": ["csv", "json", "mat", "txt"],
            },
            {
                "dataProduct": "Time Series Scalar Plot",
                "dataProductCode": "TSSP",
                "availableExtensions": ["pdf", "png"],
            },
        ],
    },
    {
        "deviceName": "Ice Buoy",
        "deviceCategoryCode": "ICE_BUOY",
        "locationCode": "CBYSP",
        "possibleDataProducts": [
            {
                "dataProduct": "Ice Buoy Profile Plots",
                "dataProductCode": "IBPP",
                "availableExtensions": ["pdf", "png"],
            },
            {
                "dataProduct": "Ice Buoy Time Series Profile Plots",
                "dataProductCode": "IBTSPP",
                "availableExtensions": ["pdf", "png"],
            },
            {
                "dataProduct": "Log File",
                "dataProductCode": "LF",
                "availableExtensions": ["txt"],
            },
            {
                "dataProduct": "Manual Scalar QAQC",
                "dataProductCode": "MSQAQCR",
                "availableExtensions": ["qaqc"],
            },
            {
                "dataProduct": "SRSL Manufacturer",
                "dataProductCode": "SRSLMF",
                "availableExtensions": ["sbd"],
            },
            {
                "dataProduct": "Time Series Scalar Data",
                "dataProductCode": "TSSD",
                "availableExtensions": ["csv", "json", "mat", "txt"],
            },
            {
                "dataProduct": "Time Series Scalar Plot",
                "dataProductCode": "TSSP",
                "availableExtensions": ["pdf", "png"],
            },
        ],
    },
    {
        "deviceName": "Automatic Identification Systems Receiver",
        "deviceCategoryCode": "AISRECEIVER",
        "locationCode": "CBYSS",
        "possibleDataProducts": [
            {
                "dataProduct": "Log File",
                "dataProductCode": "LF",
                "availableExtensions": ["txt"],
            }
        ],
    },
    {
        "deviceName": "Barometric Pressure Sensor",
        "deviceCategoryCode": "BARPRESS",
        "locationCode": "CBYSS",
        "possibleDataProducts": [
            {
                "dataProduct": "Log File",
                "dataProductCode": "LF",
                "availableExtensions": ["txt"],
            },
            {
                "dataProduct": "Manual Scalar QAQC",
                "dataProductCode": "MSQAQCR",
                "availableExtensions": ["qaqc"],
            },
            {
                "dataProduct": "Time Series Scalar Data",
                "dataProductCode": "TSSD",
                "availableExtensions": ["csv", "json", "mat", "txt"],
            },
            {
                "dataProduct": "Time Series Scalar Plot",
                "dataProductCode": "TSSP",
                "availableExtensions": ["pdf", "png"],
            },
        ],
    },
    {
        "deviceName": "Video Camera",
        "deviceCategoryCode": "VIDEOCAM",
        "locationCode": "CBYSS",
        "possibleDataProducts": [
            {
                "dataProduct": "Annotation File",
                "dataProductCode": "AF",
                "availableExtensions": ["an"],
            },
            {
                "dataProduct": "JPG File",
                "dataProductCode": "JPGF",
                "availableExtensions": ["jpg"],
            },
            {
                "dataProduct": "Log File",
                "dataProductCode": "LF",
                "availableExtensions": ["txt"],
            },
            {
                "dataProduct": "MP4 Video",
                "dataProductCode": "MP4V",
                "availableExtensions": ["mp4"],
            },
            {
                "dataProduct": "Manual Scalar QAQC",
                "dataProductCode": "MSQAQCR",
                "availableExtensions": ["qaqc"],
            },
            {
                "dataProduct": "Time Series Staircase Plot",
                "dataProductCode": "TSSCP",
                "availableExtensions": ["pdf", "png"],
            },
            {
                "dataProduct": "Time Series Scalar Data",
                "dataProductCode": "TSSD",
                "availableExtensions": ["csv", "json", "mat", "txt"],
            },
            {
                "dataProduct": "Time Series Scalar Plot",
                "dataProductCode": "TSSP",
                "availableExtensions": ["pdf", "png"],
            },
            {
                "dataProduct": "Video QAQC Results",
                "dataProductCode": "VQAQCR",
                "availableExtensions": ["an"],
            },
            {
                "dataProduct": "Video QAQCM Training Set Black",
                "dataProductCode": "VQAQCTSB",
                "availableExtensions": ["zip"],
            },
            {
                "dataProduct": "Video QAQC Training Set Focus",
                "dataProductCode": "VQAQCTSF",
                "availableExtensions": ["zip"],
            },
            {
                "dataProduct": "Video QAQC Training Set Shift Detect",
                "dataProductCode": "VQAQCTSSD",
                "availableExtensions": ["zip"],
            },
        ],
    },
    {
        "deviceName": "Internal Device Monitor",
        "deviceCategoryCode": "INTERNAL_DEVICE_MONITOR",
        "locationCode": "CBYSU",
        "possibleDataProducts": [
            {
                "dataProduct": "Log File",
                "dataProductCode": "LF",
                "availableExtensions": ["txt"],
            },
            {
                "dataProduct": "Manual Scalar QAQC",
                "dataProductCode": "MSQAQCR",
                "availableExtensions": ["qaqc"],
            },
            {
                "dataProduct": "Time Series Scalar Data",
                "dataProductCode": "TSSD",
                "availableExtensions": ["csv", "json", "mat", "txt"],
            },
            {
                "dataProduct": "Time Series Scalar Plot",
                "dataProductCode": "TSSP",
                "availableExtensions": ["pdf", "png"],
            },
        ],
    },
    {
        "deviceName": "Power Supply",
        "deviceCategoryCode": "POWER_SUPPLY",
        "locationCode": "CBYSU",
        "possibleDataProducts": [
            {
                "dataProduct": "Log File",
                "dataProductCode": "LF",
                "availableExtensions": ["txt"],
            },
            {
                "dataProduct": "Manual Scalar QAQC",
                "dataProductCode": "MSQAQCR",
                "availableExtensions": ["qaqc"],
            },
            {
                "dataProduct": "Time Series Scalar Data",
                "dataProductCode": "TSSD",
                "availableExtensions": ["csv", "json", "mat", "txt"],
            },
            {
                "dataProduct": "Time Series Scalar Plot",
                "dataProductCode": "TSSP",
                "availableExtensions": ["pdf", "png"],
            },
        ],
    },
]
