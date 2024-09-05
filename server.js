const express = require('express');
const { Pool } = require('pg');
const path = require('path');
const ejs = require('ejs');
const socketIO = require('socket.io');
const http = require('http');
const { exec } = require('child_process');


const app = express();
const server = http.createServer(app);
const io = socketIO(server);

// PostgreSQL connection pool
const pool = new Pool({
    user: 'charlieoldfield',
    host: 'localhost',
    database: 'star_jump_lottery',
    password: '',
    port: 5432,
});

// Middleware
app.use(express.static(path.join(__dirname, 'public')));
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Serve the EJS view
app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'views'));
let currentUser = null;

// Route to serve the homepage
app.get('/', (req, res) => {
    res.render('index');
});

app.post('/start-python', (req, res) => {
    exec('python3 app.py', (error, stdout, stderr) => {
        if (error) {
            console.error(`exec error: ${error.message}`);
            console.error(`stderr: ${stderr}`);
            return res.status(500).send(`Failed to start Python process: ${error.message}`);
        }
        console.log(`stdout: ${stdout}`);
        console.error(`stderr: ${stderr}`);
        // io.emit('python-started');
        res.send('Python process started');
    });
});


// Route to update star jump count
app.post('/update-star-jumps', async (req, res) => {
    const { star_jumps, user_name } = req.body;
    if (user_name) {
        currentUser = user_name;
    }
    if (!currentUser) {
        return res.status(400).send('User name is required');
    }
    console.log('Received data:', { star_jumps, user_name });

    io.emit('star-jump-update', { star_jumps });
   

    try {
        const client = await pool.connect();
        const userResult = await client.query('SELECT id FROM users WHERE user_name = $1', [currentUser]);
        let userId = userResult.rows[0]?.id;

        if (!userId) {
            const newUserResult = await client.query('INSERT INTO users(user_name) VALUES($1) RETURNING id', [currentUser]);
            userId = newUserResult.rows[0].id;
        }

        await client.query('UPDATE users SET star_jump_count = $1 WHERE id = $2', [star_jumps, userId]);
        client.release();
        res.sendStatus(200);
    } catch (err) {
        console.error('Error updating star jumps:', err);
        res.sendStatus(500);
    }
});



// Start server
const port = process.env.PORT || 3000;
server.listen(port, () => {
    console.log(`Server running on port ${port}`);
});
