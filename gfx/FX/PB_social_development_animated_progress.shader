Includes = {
}

PixelShader =
{
	Samplers =
	{
		TextureOne =
		{
			Index = 0
			MagFilter = "Point"
			MinFilter = "Point"
			MipFilter = "None"
			AddressU = "Wrap"
			AddressV = "Wrap"
		}
		TextureTwo =
		{
			Index = 1
			MagFilter = "Point"
			MinFilter = "Point"
			MipFilter = "None"
			AddressU = "Wrap"
			AddressV = "Wrap"
		}
	}
}


VertexStruct VS_INPUT
{
    float4 vPosition  : POSITION;
    float2 vTexCoord  : TEXCOORD0;
};

VertexStruct VS_OUTPUT
{
    float4  vPosition : PDX_POSITION;
    float2  vTexCoord0 : TEXCOORD0;
};


ConstantBuffer( 0, 0 )
{
	float4x4 WorldViewProjectionMatrix;
	float4 vFirstColor;
	float4 vSecondColor;
	float CurrentState;
	float Time;
	float AnimationTime;
};


VertexShader =
{
	MainCode VertexShaderMain
	[[
		VS_OUTPUT main(const VS_INPUT v )
		{
			VS_OUTPUT Out;
		   	Out.vPosition  = mul( WorldViewProjectionMatrix, v.vPosition );
			Out.vTexCoord0  = v.vTexCoord;
			Out.vTexCoord0.y = -Out.vTexCoord0.y;
			return Out;
		}
	]]
}

PixelShader =
{
	MainCode PixelShaderMain
	[[
		float4 main( VS_OUTPUT v ) : PDX_COLOR
		{
			float vProgress = mod(CurrentState * 1000000.f, 1000.f) / 100.f;
			float vPrevProgress = floor(CurrentState * 1000.f) / 100.f;
			float vTime = Time - AnimationTime;
			float vFactor = 2.f;
			if(v.vTexCoord0.x <= vProgress && v.vTexCoord0.x <= sin(clamp(vTime, 0, 1) * vFactor * 1.5708f) - vPrevProgress / vFactor){
				return tex2D(TextureOne, v.vTexCoord0);
			}
			return tex2D(TextureTwo, v.vTexCoord0);
		}
	]]
}

BlendState BlendState
{
	BlendEnable = yes
	SourceBlend = "SRC_ALPHA"
	DestBlend = "INV_SRC_ALPHA"
}


Effect Color
{
	VertexShader = "VertexShaderMain"
	PixelShader = "PixelShaderMain"
}

Effect Texture
{
	VertexShader = "VertexShaderMain"
	PixelShader = "PixelShaderMain"
}

