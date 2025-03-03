const { exec } = require('child_process');

module.exports = (srv) => {


    srv.on("askSQL", async (req) => {
        const { question } = req.data;
        const sanitizedQuestion = question.replace(/"/g, '\\"'); // Prevenir problemas com aspas
    
        return new Promise((resolve, reject) => {
          exec(`python3 srv/sql_agent.py "${sanitizedQuestion}"`, (error, stdout, stderr) => {
            if (error || stderr) {
              console.error(`Erro ao executar Python: ${stderr || error.message}`);
              reject("Erro ao processar a pergunta.");
              return;
            }
            console.log(`Resposta do modelo SQL: ${stdout.trim()}`);
            resolve(stdout.trim());
          });
        });
      });

    srv.on('order', async (req) => {
        const { orderID } = req.data;

        return new Promise((resolve, reject) => {
            exec(`python3 srv/script.py approve ${orderID}`, (error, stdout, stderr) => {
                if (error) {
                    console.error(`Erro ao aprovar a ordem: ${stderr}`);
                    reject("Erro ao aprovar a ordem.");
                } else {
                    console.log(`Ordem aprovada: ${stdout}`);
                    resolve(`Ordem ${orderID} aprovada com sucesso.`);
                }
            });
        });
        
    });

    const { exec } = require('child_process');


    srv.on('askAI', async (req) => {
        const { question } = req.data;

        return new Promise((resolve, reject) => {
            exec(`python3 srv/groq_model.py "${question}"`, (error, stdout, stderr) => {
                if (error) {
                    console.error(`Erro ao executar Python: ${stderr}`);
                    reject("Erro ao processar a pergunta.");
                    return;
                }
                if (stderr) {
                    console.error(`Erro no script Python: ${stderr}`);
                    reject(stderr);
                    return;
                }
                console.log(`Resposta do modelo: ${stdout.trim()}`);
                resolve(stdout.trim());  // Retorna a resposta gerada
            });
        });
    });

};

