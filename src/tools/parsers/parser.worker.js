// Worker.js
// import MavlinkParser from 'mavlinkParser'
const mavparser = require('./mavlinkParser')
const DataflashParser = require('./JsDataflashParser/parser').default
const DjiParser = require('./djiParser').default

let parser
let parsedData = null

self.addEventListener('message', async function (event) {
    if (event.data === null) {
        console.log('got bad file message!')
    } else if (event.data.action === 'parse') {
        console.log('parsing file')
        const data = event.data.file
        if (event.data.isTlog) {
            parser = new mavparser.MavlinkParser()
            parsedData = parser.processData(data)
        } else if (event.data.isDji) {
            parser = new DjiParser()
            parsedData = await parser.processData(data)
        } else {
            parser = new DataflashParser(true)
            parsedData = parser.processData(data, ['CMD', 'MSG', 'FILE', 'MODE', 'AHR2', 'ATT', 'GPS', 'POS',
                'XKQ1', 'XKQ', 'NKQ1', 'NKQ2', 'XKQ2', 'PARM', 'MSG', 'STAT', 'EV', 'XKF4', 'FNCE'])
        }
        console.log('Done parsing file - all data will be sent to backend in single request')

    } else if (event.data.action === 'loadType') {
        if (!parser) {
            console.log('parser not ready')
        }
        parser.loadType(event.data.type.split('[')[0])
    } else if (event.data.action === 'trimFile') {
        parser.trimFile(event.data.time)
    }
})
