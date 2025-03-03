const { exec } = require('child_process');
const cds = require('@sap/cds');

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


    srv.before('CREATE', 'orders', async (req) => {
        try {
          const { valor_total, fornecedor_ID } = req.data;
      
          console.log("==DEBUG== [before CREATE orders] Dados recebidos da nova ordem:", req.data);
      
          if (!fornecedor_ID) {
            console.log("Nenhum fornecedor_ID. A ordem ficará REJEITADA ou PENDENTE.");
            req.data.status = "REJEITADO";
            return;
          }
      
          const cmd = `python3 srv/sql_agent.py ${valor_total} ${fornecedor_ID}`;
          console.log("==DEBUG== [before CREATE orders] Comando a executar:", cmd);
      
          const result = await new Promise((resolve, reject) => {
            exec(cmd, (error, stdout, stderr) => {
              if (error) {
                console.error("==ERRO== Script Python falhou:", stderr || error.message);
                return reject(error);
              }
              return resolve(stdout.trim());
            });
          });
      
          console.log("==DEBUG== [before CREATE orders] Resposta do LLM:", result);
      
          if (result.includes("APROVAR")) {
            req.data.status = "APROVADO";
          } else {
            req.data.status = "REJEITADO";
          }
      
        } catch (err) {
          console.error("Falha ao verificar aprovação automática:", err);
          req.data.status = "REJEITADO";
        }
      });
      


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



