using {
  cuid,
  managed
} from '@sap/cds/common';

context my.orders {

  entity Fornecedor : managed, cuid {
    name        : String;   // Nome do fornecedor
    nif         : String(9); // NIF do fornecedor
    email       : String;   // Email do fornecedor
    telefone    : String(15); // Telefone do fornecedor
    ativo       : Boolean default true; // Estado do fornecedor 
    orders      : Composition of many Order on orders.fornecedor = $self; 
  }

  entity Order : managed, cuid {
    numero              : String(20);  // Número da ordem de compra
    data                : DateTime;    // Data da ordem
    valor_total         : Decimal(15,2); // Valor total da ordem
    status              : String enum {
      PENDENTE;
      APROVADO;
      REJEITADO;
    }; 
    fornecedor          : Association to Fornecedor; 
    previsao_entrega    : DateTime; // Data de previsão de entrega
    data_entrega        : DateTime; // Data real da entrega
    materiais           : Composition of many OrderMaterial on materiais.order = $self;
  }

  entity Material : managed, cuid {
    codigo         : String(20);  // Código do material
    descricao      : String;      // Descrição do material
    unidade_medida : String(5);   // Unidade de medida (ex: KG, L, UN)
    preco_unitario : Decimal(10,2); // Preço unitário do material
  }

entity OrderMaterial : managed, cuid {
    order       : Association to Order;
    material    : Association to Material;
    quantidade  : Integer; 
    preco_unitario : Decimal(10,2); // Agora é armazenado por ordem
    subtotal    : Decimal(15,2);
}


}
