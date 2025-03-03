const { exec } = require('child_process');
const cds = require('@sap/cds');

module.exports = (srv) => {

    // Ação para perguntas em SQL via Python
    srv.on("askSQL", async (req) => {
        const { question } = req.data;
        const sanitizedQuestion = question.replace(/"/g, '\\"'); // Prevenir problemas com aspas

        return new Promise((resolve, reject) => {
            exec(`python3 srv/sql_agentv1.py "${sanitizedQuestion}"`, (error, stdout, stderr) => {
                if (error || stderr) {
                    console.error(`Erro ao executar Python: ${stderr || error.message}`);
                    return reject("Erro ao processar a pergunta.");
                }
                console.log(`Resposta do modelo SQL: ${stdout.trim()}`);
                resolve(stdout.trim());
            });
        });
    });

    // Hook antes da criação de uma ordem
    srv.before('CREATE', 'orders', async (req) => {
        try {
            const { valor_total, fornecedor_ID, previsao_entrega, data_entrega } = req.data;
        
            console.log("==DEBUG== [before CREATE orders] Dados recebidos da nova ordem:", req.data);
        
            if (!fornecedor_ID) {
                console.log("Nenhum fornecedor_ID. A ordem ficará REJEITADA.");
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
        
            req.data.status = result.includes("APROVAR") ? "APROVADO" : "REJEITADO";

            // Verifica se há datas de entrega e previsão
            if (!previsao_entrega) {
                console.log("Nenhuma data de previsão de entrega fornecida.");
                req.data.previsao_entrega = null; // Garantir que não causa erro no CDS
            }

            if (!data_entrega) {
                console.log("Nenhuma data de entrega fornecida.");
                req.data.data_entrega = null; // Garantir que não causa erro no CDS
            }

        } catch (err) {
            console.error("Falha ao verificar aprovação automática:", err);
            req.data.status = "REJEITADO";
        }
    });

    // Ação para perguntas gerais à IA via Python
    srv.on('askAI', async (req) => {
        const { question } = req.data;

        return new Promise((resolve, reject) => {
            exec(`python3 srv/groq_model.py "${question}"`, (error, stdout, stderr) => {
                if (error || stderr) {
                    console.error(`Erro ao executar Python: ${stderr || error.message}`);
                    return reject("Erro ao processar a pergunta.");
                }
                console.log(`Resposta do modelo: ${stdout.trim()}`);
                resolve(stdout.trim());
            });
        });
    });

    // Hook para calcular o subtotal antes da criação de OrderMaterial
    srv.before('CREATE', 'orderMateriais', async (req) => {
        try {
            const { material_ID, quantidade } = req.data;
            console.log("==DEBUG== [before CREATE orderMateriais] Dados recebidos:", req.data);

            if (!material_ID || !quantidade) {
                console.error("==ERRO== Material ou quantidade não fornecidos.");
                req.reject(400, "Material e quantidade são obrigatórios.");
                return;
            }

            // Buscar preço unitário do material
            const material = await cds.run(SELECT.one.from('my.orders.Material').where({ ID: material_ID }));
            if (!material) {
                console.error("==ERRO== Material não encontrado.");
                req.reject(400, "Material não encontrado.");
                return;
            }

            // Calcular subtotal
            req.data.subtotal = (material.preco_unitario * quantidade).toFixed(2);
            console.log("==DEBUG== [before CREATE orderMateriais] Subtotal calculado:", req.data.subtotal);
        } catch (err) {
            console.error("==ERRO== Falha ao calcular subtotal:", err);
            req.reject(500, "Erro interno ao calcular subtotal.");
        }
    });
    

};
